"""
cli.py
======
Click-based CLI entry points registered in pyproject.toml.
These are the commands invoked by the DABs python_wheel_task definitions.

  scan_drift    → databricks.yml iceberg_schema_drift_scan
  sync_catalog  → databricks.yml iceberg_catalog_sync

Each command is intentionally thin: parse args, construct domain objects,
call the library, emit structured JSON output to stdout for Databricks
job logs, exit non-zero on failure.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Optional

import click

from databricks.sdk import WorkspaceClient
from iceberg_catalog.polaris_client import PolarisClient
from iceberg_catalog.schema_sync import IcebergSchemaSync
from iceberg_catalog.table_migration import IcebergTableRegistrar

try:
    from databricks.sdk.runtime import dbutils
except ImportError:
    dbutils = None  # Only available in Databricks runtime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("iceberg_catalog.cli")


# ── scan_drift ─────────────────────────────────────────────────────────────────

@click.command("scan_drift")
@click.option("--uc-sf-catalog",      required=True, help="UC foreign catalog name (Snowflake-side)")
@click.option("--uc-db-catalog",      required=True, help="UC managed catalog name (Databricks-side)")
@click.option("--secret-scope",       required=True, help="Databricks secret scope for Polaris creds")
@click.option("--snowflake-account",  required=True, help="Snowflake account identifier")
@click.option("--principal-role",     default="databricks_svc_role", show_default=True)
@click.option("--polaris-catalog",    default="ICEBERG_LAKEHOUSE",  show_default=True)
@click.option("--apply-safe-changes", is_flag=True, default=True,
              help="Auto-apply non-breaking schema changes to Polaris")
@click.option("--fail-on-drift",      is_flag=True, default=False,
              help="Exit non-zero if any drift is detected (useful for CI gates)")
def scan_drift(
    uc_sf_catalog:     str,
    uc_db_catalog:     str,
    secret_scope:      str,
    snowflake_account: str,
    principal_role:    str,
    polaris_catalog:   str,
    apply_safe_changes: bool,
    fail_on_drift:     bool,
) -> None:
    """Detect schema drift between UC and Snowflake Open Catalog (Polaris)."""
    w = WorkspaceClient()
    polaris = PolarisClient.from_secrets(
        snowflake_account = snowflake_account,
        secret_scope      = secret_scope,
        principal_role    = principal_role,
        catalog_name      = polaris_catalog,
    )
    sync = IcebergSchemaSync(polaris, w)

    logger.info("Scanning all tables in UC catalog: %s", uc_sf_catalog)
    drift_reports = sync.scan_all_tables(uc_sf_catalog)

    total          = len(drift_reports)
    has_drift      = [r for r in drift_reports if r.has_drift]
    has_breaking   = [r for r in drift_reports if r.has_breaking_drift]
    safe_to_apply  = [r for r in has_drift if not r.has_breaking_drift]

    summary = {
        "total_tables_scanned": total,
        "tables_with_drift":    len(has_drift),
        "tables_with_breaking": len(has_breaking),
        "tables_safe_to_apply": len(safe_to_apply),
        "breaking": [
            {"table": f"{r.catalog}.{r.schema}.{r.table}",
             "drifts": [{"col": d.column_name, "kind": d.kind.value} for d in r.drifts if d.is_breaking]}
            for r in has_breaking
        ],
    }
    print(json.dumps(summary, indent=2))

    if apply_safe_changes and safe_to_apply:
        logger.info("Applying safe schema changes to %d table(s)", len(safe_to_apply))
        for report in safe_to_apply:
            try:
                sync.apply_compatible_changes(report)
            except Exception as e:
                logger.error("Could not apply changes to %s.%s.%s: %s",
                             report.catalog, report.schema, report.table, e)

    if has_breaking:
        logger.error(
            "BREAKING SCHEMA DRIFT detected on %d table(s) — manual review required:\n%s",
            len(has_breaking),
            "\n".join(r.summary() for r in has_breaking),
        )
        sys.exit(2)   # distinct exit code so Databricks alert can distinguish

    if fail_on_drift and has_drift:
        logger.warning("Schema drift detected on %d table(s) (non-breaking)", len(has_drift))
        sys.exit(1)

    logger.info("Schema scan complete. %d table(s) checked, %d with drift.", total, len(has_drift))


# ── sync_catalog ───────────────────────────────────────────────────────────────

@click.command("sync_catalog")
@click.option("--uc-catalog",         required=True, help="UC managed Iceberg catalog (Databricks-authored)")
@click.option("--schemas",            required=True, help="Comma-separated list of schemas to sync")
@click.option("--sf-polaris-catalog", required=True, help="Snowflake Open Catalog name")
@click.option("--secret-scope",       required=True, help="Databricks secret scope for Snowflake creds")
@click.option("--sf-warehouse",       default="COMPUTE_WH", show_default=True)
@click.option("--sf-external-volume", default="ICEBERG_VOL", show_default=True)
@click.option("--dry-run",            is_flag=True,  default=False,
              help="Print what would be registered/refreshed without executing")
def sync_catalog(
    uc_catalog:         str,
    schemas:            str,
    sf_polaris_catalog: str,
    secret_scope:       str,
    sf_warehouse:       str,
    sf_external_volume: str,
    dry_run:            bool,
) -> None:
    """Register or refresh all Databricks-authored Iceberg tables in Snowflake."""
    if dbutils is None:
        raise RuntimeError("sync_catalog must run on Databricks (dbutils not available)")
    schema_list = [s.strip() for s in schemas.split(",") if s.strip()]
    w = WorkspaceClient()

    registrar = IcebergTableRegistrar(
        uc_client=w,
        sf_account=dbutils.secrets.get(secret_scope, "snowflake_account"),
        sf_user            = dbutils.secrets.get(secret_scope, "sf_user"),
        sf_password        = dbutils.secrets.get(secret_scope, "sf_password"),
        sf_warehouse       = sf_warehouse,
        sf_polaris_catalog = sf_polaris_catalog,
        sf_external_volume = sf_external_volume,
    )

    if dry_run:
        logger.info("[DRY RUN] Would sync catalog %s schemas: %s", uc_catalog, schema_list)
        # Still resolve locations so we know what would be synced
        for schema in schema_list:
            try:
                tables = list(w.tables.list(catalog_name=uc_catalog, schema_name=schema))
                for t in tables:
                    if hasattr(t, "data_source_format") and str(t.data_source_format).upper() == "ICEBERG":
                        logger.info("[DRY RUN]   would sync: %s.%s.%s", uc_catalog, schema, t.name)
            except Exception as e:
                logger.warning("[DRY RUN] Could not list %s.%s: %s", uc_catalog, schema, e)
        return

    locations = registrar.sync_catalog(uc_catalog, schema_list)

    summary = {
        "synced_tables": len(locations),
        "tables": [
            {
                "fqn":               f"{loc.catalog}.{loc.schema}.{loc.table}",
                "metadata_location": loc.metadata_location,
                "snapshot_id":       loc.snapshot_id,
            }
            for loc in locations
        ],
    }
    print(json.dumps(summary, indent=2))
    logger.info("Catalog sync complete: %d table(s) registered/refreshed", len(locations))
