"""
table_migration.py
==================
Utilities for:
  1. Discovering the current Iceberg metadata.json path for a UC-managed table
     (needed when registering Databricks-authored tables in Snowflake)
  2. Automating the Snowflake REGISTER ICEBERG TABLE call via the Snowflake
     Python connector

WHY this is needed:
  When Databricks writes an Iceberg table, it commits a new metadata.json
  pointer to the metadata log.  Snowflake's REGISTER ICEBERG TABLE command
  requires you to supply the exact S3 path to that metadata.json.  Without
  automation, an operator would have to manually ls the S3 metadata/ directory
  after every Databricks job run and paste the path — error-prone and unscalable
  across 19+ business units.

  This module resolves the current metadata pointer programmatically and
  handles the registration + subsequent refresh lifecycle.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import boto3
import snowflake.connector
from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)


@dataclass
class TableLocation:
    catalog:           str
    schema:            str
    table:             str
    s3_base_location:  str    # e.g. s3://iceberg-lakehouse/iceberg/.../finops/pipeline_runs
    metadata_location: str    # e.g. s3://.../.../metadata/00003-<uuid>.metadata.json
    snapshot_id:       int | None = None
    schema_id:         int | None = None


class IcebergTableRegistrar:
    """
    Discovers Databricks Iceberg table locations and registers/refreshes them
    in Snowflake.

    Usage::

        reg = IcebergTableRegistrar(
            uc_client          = WorkspaceClient(),
            sf_account         = "example.us-west-2.aws",
            sf_user            = "svc_iceberg",
            sf_password        = dbutils.secrets.get("vault", "sf_pw"),
            sf_warehouse       = "COMPUTE_WH",
            sf_polaris_catalog = "ICEBERG_LAKEHOUSE",
        )
        loc = reg.get_table_location("iceberg_db", "finops", "pipeline_runs")
        reg.register_or_refresh_in_snowflake(loc)
    """

    def __init__(
        self,
        uc_client:           WorkspaceClient,
        sf_account:          str,
        sf_user:             str,
        sf_password:         str,
        sf_warehouse:        str,
        sf_polaris_catalog:  str,
        sf_external_volume:  str = "ICEBERG_VOL",
    ) -> None:
        self._uc                 = uc_client
        self._sf_account         = sf_account
        self._sf_user            = sf_user
        self._sf_password        = sf_password
        self._sf_warehouse       = sf_warehouse
        self._sf_polaris_catalog = sf_polaris_catalog
        self._sf_external_volume = sf_external_volume
        self._s3 = boto3.client("s3")   # uses instance profile / env credentials

    # ── UC metadata location ──────────────────────────────────────────────────

    def get_table_location(self, catalog: str, schema: str, table: str) -> TableLocation:
        """
        Resolve the current Iceberg metadata.json path for a UC-managed Iceberg table.

        UC stores the metadata location in the table's storage properties.
        We retrieve it via the UC Tables API, then parse the metadata.json from S3
        to get the current snapshot ID.
        """
        fqn = f"{catalog}.{schema}.{table}"
        try:
            uc_table = self._uc.tables.get(fqn)
        except Exception as e:
            raise ValueError(f"UC table not found: {fqn}") from e

        # UC exposes the table's S3 location
        base_location = uc_table.storage_location
        if not base_location:
            raise ValueError(f"UC table {fqn} has no storage_location (is it a managed Iceberg table?)")

        # Parse s3://bucket/key
        bucket, prefix = self._parse_s3_uri(base_location)

        # Find the current metadata.json — it's the file referenced by
        # metadata/version-hint.text (if present) or the latest .metadata.json
        metadata_path = self._resolve_current_metadata(bucket, prefix)

        # Read the metadata to get snapshot ID + schema ID
        snapshot_id, schema_id = self._read_metadata_snapshot(bucket, metadata_path)

        return TableLocation(
            catalog           = catalog,
            schema            = schema,
            table             = table,
            s3_base_location  = base_location.rstrip("/"),
            metadata_location = f"s3://{bucket}/{metadata_path}",
            snapshot_id       = snapshot_id,
            schema_id         = schema_id,
        )

    def _parse_s3_uri(self, uri: str) -> tuple[str, str]:
        """Parse 's3://bucket/prefix' → ('bucket', 'prefix')."""
        if not uri.startswith("s3://"):
            raise ValueError(f"Expected s3:// URI, got: {uri}")
        without_scheme = uri[5:]
        bucket, _, prefix = without_scheme.partition("/")
        return bucket, prefix.rstrip("/")

    def _resolve_current_metadata(self, bucket: str, table_prefix: str) -> str:
        """
        Return the S3 key of the current metadata.json.

        Iceberg writes a 'metadata/version-hint.text' file containing the
        version number of the current metadata file.  If not present (Spark
        default doesn't always write it), fall back to lexicographic latest.
        """
        metadata_prefix = f"{table_prefix}/metadata/"

        # Try version-hint.text first
        try:
            resp = self._s3.get_object(Bucket=bucket, Key=f"{metadata_prefix}version-hint.text")
            version = int(resp["Body"].read().decode().strip())
            # List files matching the version prefix
            paginator = self._s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket, Prefix=f"{metadata_prefix}{version:05d}-"):
                for obj in page.get("Contents", []):
                    if obj["Key"].endswith(".metadata.json"):
                        return obj["Key"]
        except self._s3.exceptions.NoSuchKey:
            pass

        # Fallback: lexicographic latest .metadata.json
        paginator = self._s3.get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=bucket, Prefix=metadata_prefix):
            for obj in page.get("Contents", []):
                if obj["Key"].endswith(".metadata.json"):
                    keys.append(obj["Key"])

        if not keys:
            raise FileNotFoundError(
                f"No .metadata.json files found at s3://{bucket}/{metadata_prefix}"
            )
        return sorted(keys)[-1]   # lexicographic sort is version-monotone for Iceberg

    def _read_metadata_snapshot(self, bucket: str, metadata_key: str) -> tuple[int | None, int | None]:
        """Read metadata.json from S3 and extract the current snapshot ID + schema ID."""
        try:
            resp = self._s3.get_object(Bucket=bucket, Key=metadata_key)
            meta = json.loads(resp["Body"].read())
            return (
                meta.get("current-snapshot-id"),
                meta.get("current-schema-id"),
            )
        except Exception as e:
            logger.warning("Could not read metadata.json: %s", e)
            return None, None

    # ── Snowflake registration / refresh ─────────────────────────────────────

    def _sf_conn(self) -> snowflake.connector.SnowflakeConnection:
        return snowflake.connector.connect(
            account   = self._sf_account,
            user      = self._sf_user,
            password  = self._sf_password,
            warehouse = self._sf_warehouse,
            role      = "SYSADMIN",
        )

    def _is_registered_in_snowflake(
        self, conn: snowflake.connector.SnowflakeConnection, namespace: str, table: str
    ) -> bool:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT COUNT(*) FROM {self._sf_polaris_catalog}.INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = UPPER('{namespace}')
                  AND TABLE_NAME   = UPPER('{table}')
            """)
            return cur.fetchone()[0] > 0

    def register_or_refresh_in_snowflake(self, loc: TableLocation) -> None:
        """
        Register a new Databricks-authored Iceberg table in Snowflake, or
        refresh an existing one to pick up new snapshots.

        Snowflake semantics:
          - REGISTER ICEBERG TABLE: first-time only; fails if table exists
          - ALTER TABLE ... REFRESH: subsequent runs after Databricks writes
        """
        conn = self._sf_conn()
        ns   = loc.schema.upper()
        tbl  = loc.table.upper()
        fqsf = f"{self._sf_polaris_catalog}.{ns}.{tbl}"

        if self._is_registered_in_snowflake(conn, loc.schema, loc.table):
            logger.info("Table %s exists in Snowflake — refreshing metadata", fqsf)
            sql = f"""
                ALTER ICEBERG TABLE {fqsf}
                REFRESH METADATA_FILE_PATH = '{loc.metadata_location}'
            """
        else:
            logger.info("Registering new Iceberg table %s in Snowflake", fqsf)
            sql = f"""
                REGISTER ICEBERG TABLE {fqsf}
                  CATALOG           = '{self._sf_polaris_catalog}'
                  EXTERNAL_VOLUME   = '{self._sf_external_volume}'
                  METADATA_FILE_PATH = '{loc.metadata_location}'
            """

        with conn.cursor() as cur:
            cur.execute(sql)
        logger.info("Snowflake registration/refresh complete for %s → %s", fqsf, loc.metadata_location)
        conn.close()

    def sync_catalog(self, uc_catalog: str, schemas: list[str]) -> list[TableLocation]:
        """
        Discover all Iceberg tables in the given UC catalog/schemas and
        register or refresh each one in Snowflake.  Returns the list of
        resolved locations for audit logging.
        """
        locations: list[TableLocation] = []
        conn = self._sf_conn()

        try:
            for schema in schemas:
                # List tables via UC
                try:
                    tables = list(self._uc.tables.list(catalog_name=uc_catalog, schema_name=schema))
                except Exception as e:
                    logger.warning("Could not list tables in %s.%s: %s", uc_catalog, schema, e)
                    continue

                for t in tables:
                    # Only process Iceberg tables (UC table_type EXTERNAL + provider ICEBERG)
                    if not (hasattr(t, "data_source_format") and
                            str(t.data_source_format).upper() == "ICEBERG"):
                        continue
                    try:
                        loc = self.get_table_location(uc_catalog, schema, t.name)
                        self.register_or_refresh_in_snowflake(loc)
                        locations.append(loc)
                    except Exception as e:
                        logger.error("Failed to sync %s.%s.%s: %s", uc_catalog, schema, t.name, e)
        finally:
            conn.close()

        return locations
