"""
snowflake_refresh.py
====================
Event-driven Snowflake Iceberg table refresh client.

WHY event-driven vs. polling (Snowflake Task):
  The Snowflake Task approach (see 05_register_databricks_tables.sql) polls
  every N minutes, which wastes Snowflake credits and introduces latency.
  The correct pattern for Databricks → Snowflake is:
    1. Databricks job writes to S3 (commits new Iceberg snapshot)
    2. Databricks job calls SnowflakeRefreshClient.refresh_table() at the
       end of the task — zero polling lag, zero wasted credits
    3. Snowflake immediately reflects the new data

  This module is meant to be called from the Databricks Workflow task that
  writes the Iceberg table, NOT from Snowflake's scheduler.

Integration pattern in a Databricks job:

    # At the end of your pipeline notebook/task:
    from iceberg_catalog import SnowflakeRefreshClient, IcebergTableRegistrar
    from databricks.sdk import WorkspaceClient

    registrar = IcebergTableRegistrar(...)
    loc = registrar.get_table_location("iceberg_db", "finops", "pipeline_runs")

    refresher = SnowflakeRefreshClient.from_secrets("iceberg-polaris")
    refresher.refresh_table(loc)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import snowflake.connector

from iceberg_catalog.table_migration import (
    TableLocation,
    _validate_metadata_location,
    _validate_snowflake_identifier,
)

logger = logging.getLogger(__name__)


@dataclass
class RefreshResult:
    table_fqn:         str
    metadata_location: str
    success:           bool
    error_message:     str | None = None


class SnowflakeRefreshClient:
    """
    Triggers Snowflake to refresh its view of a Databricks-authored Iceberg
    table by issuing ALTER TABLE ... REFRESH METADATA_FILE_PATH.

    Lightweight: opens a connection, runs one statement, closes.
    Designed to be called at the tail of any Databricks job that writes Iceberg.
    """

    def __init__(
        self,
        sf_account:          str,
        sf_user:             str,
        sf_password:         str,
        sf_warehouse:        str,
        sf_polaris_catalog:  str,
        sf_role:             str = "SYSADMIN",
    ) -> None:
        self._sf_account        = sf_account
        self._sf_user           = sf_user
        self._sf_password       = sf_password
        self._sf_warehouse      = sf_warehouse
        self._sf_polaris_catalog = sf_polaris_catalog
        self._sf_role           = sf_role

    @classmethod
    def from_secrets(
        cls,
        secret_scope:        str,
        sf_polaris_catalog:  str = "ICEBERG_LAKEHOUSE",
        sf_warehouse:        str = "COMPUTE_WH",
    ) -> SnowflakeRefreshClient:
        """Construct from Databricks secrets (for use in Databricks runtime)."""
        try:
            from databricks.sdk.runtime import dbutils  # noqa
        except ImportError:
            raise RuntimeError("from_secrets() requires Databricks runtime") from None

        return cls(
            sf_account         = dbutils.secrets.get(secret_scope, "snowflake_account"),
            sf_user            = dbutils.secrets.get(secret_scope, "sf_user"),
            sf_password        = dbutils.secrets.get(secret_scope, "sf_password"),
            sf_warehouse       = sf_warehouse,
            sf_polaris_catalog = sf_polaris_catalog,
        )

    def refresh_table(self, loc: TableLocation) -> RefreshResult:
        """
        Refresh a single Snowflake-registered Iceberg table to point at
        the latest metadata committed by Databricks.
        """
        ns = _validate_snowflake_identifier(loc.schema, "schema").upper()
        tbl = _validate_snowflake_identifier(loc.table, "table").upper()
        meta_path = _validate_metadata_location(loc.metadata_location)
        fqsf = f"{self._sf_polaris_catalog}.{ns}.{tbl}"

        try:
            conn = snowflake.connector.connect(
                account   = self._sf_account,
                user      = self._sf_user,
                password  = self._sf_password,
                warehouse = self._sf_warehouse,
                role      = self._sf_role,
            )
            with conn.cursor() as cur:
                cur.execute(f"""
                    ALTER ICEBERG TABLE {fqsf}
                    REFRESH METADATA_FILE_PATH = '{meta_path}'
                """)
            conn.close()

            logger.info("Refreshed %s → %s", fqsf, meta_path)
            return RefreshResult(
                table_fqn         = fqsf,
                metadata_location = loc.metadata_location,
                success           = True,
            )

        except Exception as e:
            logger.error("Refresh failed for %s: %s", fqsf, e)
            return RefreshResult(
                table_fqn         = fqsf,
                metadata_location = loc.metadata_location,
                success           = False,
                error_message     = str(e),
            )

    def refresh_batch(self, locations: list[TableLocation]) -> list[RefreshResult]:
        """Refresh multiple tables in a single Snowflake session (more efficient)."""
        if not locations:
            return []

        results: list[RefreshResult] = []
        try:
            conn = snowflake.connector.connect(
                account   = self._sf_account,
                user      = self._sf_user,
                password  = self._sf_password,
                warehouse = self._sf_warehouse,
                role      = self._sf_role,
            )
            with conn.cursor() as cur:
                for loc in locations:
                    ns = _validate_snowflake_identifier(loc.schema, "schema").upper()
                    tbl = _validate_snowflake_identifier(loc.table, "table").upper()
                    meta_path = _validate_metadata_location(loc.metadata_location)
                    fqsf = f"{self._sf_polaris_catalog}.{ns}.{tbl}"
                    try:
                        cur.execute(f"""
                            ALTER ICEBERG TABLE {fqsf}
                            REFRESH METADATA_FILE_PATH = '{meta_path}'
                        """)
                        logger.info("Refreshed %s", fqsf)
                        results.append(RefreshResult(
                            table_fqn=fqsf, metadata_location=loc.metadata_location, success=True
                        ))
                    except Exception as e:
                        logger.error("Refresh failed for %s: %s", fqsf, e)
                        results.append(RefreshResult(
                            table_fqn=fqsf, metadata_location=loc.metadata_location,
                            success=False, error_message=str(e)
                        ))
            conn.close()

        except Exception as e:
            logger.error("Snowflake connection failed during batch refresh: %s", e)
            for loc in locations:
                fqsf = f"{self._sf_polaris_catalog}.{loc.schema.upper()}.{loc.table.upper()}"
                results.append(RefreshResult(
                    table_fqn=fqsf, metadata_location=loc.metadata_location,
                    success=False, error_message=f"Connection error: {e}"
                ))

        return results
