# Databricks notebook source
# databricks/bundle/notebooks/expire_iceberg_snapshots.py
#
# WHY Iceberg snapshot expiry matters:
#   Every Iceberg write (INSERT, UPDATE, MERGE, OPTIMIZE) creates a new
#   snapshot.  The data files referenced by old snapshots are NOT deleted
#   until you explicitly expire them.  On a typical FinOps pipeline — which
#   runs daily — the subscriber_events and invoice_line_items tables will
#   accumulate hundreds of snapshots per month, each retaining references to
#   now-redundant Parquet files on S3.  At $0.023/GB/month this becomes
#   material within weeks.
#
#   expire_snapshots() removes snapshot metadata entries older than the
#   retention window AND deletes the S3 objects for data files that are no
#   longer referenced by any live snapshot.
#
#   IMPORTANT: Run this BEFORE the S3 lifecycle policy's noncurrent_version_
#   expiration fires (set to 90 days in Terraform), otherwise S3 may delete
#   files that Iceberg still considers live in an intermediate snapshot.

# COMMAND ----------

import logging
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# COMMAND ----------

# Widget defaults — overridden by DABs base_parameters
dbutils.widgets.text("uc_catalog",      "iceberg_db")
dbutils.widgets.text("retention_hours", "168")   # 7 days
dbutils.widgets.text("dry_run",         "false")

import re

_ID_RE = re.compile(r"^[a-zA-Z0-9_]+$")
def _validate_id(name, kind="identifier"):
    if not _ID_RE.match(name):
        raise ValueError(f"{kind} contains invalid characters: {name!r}")
    return name

uc_catalog       = _validate_id(dbutils.widgets.get("uc_catalog"), "catalog")
retention_hours  = int(dbutils.widgets.get("retention_hours"))
dry_run          = dbutils.widgets.get("dry_run").lower() == "true"

cutoff_ts = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
cutoff_ms = int(cutoff_ts.timestamp() * 1000)   # Iceberg uses milliseconds

logger.info("Expiring snapshots older than %s (%dh retention)", cutoff_ts.isoformat(), retention_hours)
logger.info("Dry run: %s", dry_run)

# COMMAND ----------

# Discover all Iceberg tables in the managed catalog
schemas = spark.sql(f"SHOW SCHEMAS IN {uc_catalog}").collect()
schema_names = [row["databaseName"] for row in schemas]

logger.info("Found %d schemas in %s: %s", len(schema_names), uc_catalog, schema_names)

# COMMAND ----------

results = []

for schema_name in schema_names:
    tables = spark.sql(f"SHOW TABLES IN {uc_catalog}.{schema_name}").collect()

    for row in tables:
        fqn = f"{uc_catalog}.{schema_name}.{row['tableName']}"

        # Only Iceberg tables support expire_snapshots
        try:
            props = spark.sql(f"DESCRIBE EXTENDED {fqn}").filter(
                "col_name = 'Provider'"
            ).collect()
            if not props or props[0]["data_type"].upper() != "ICEBERG":
                continue
        except Exception:
            continue

        # Count snapshots before expiry
        try:
            before_count = spark.sql(
                f"SELECT COUNT(*) AS n FROM {fqn}.snapshots"
            ).collect()[0]["n"]
        except Exception:
            before_count = -1

        if dry_run:
            logger.info("[DRY RUN] Would expire snapshots older than %s on %s (currently %d snapshots)",
                        cutoff_ts.isoformat(), fqn, before_count)
            results.append({"table": fqn, "action": "dry_run", "snapshots_before": before_count})
            continue

        try:
            # expire_snapshots: removes snapshot entries AND unreferenced data files
            spark.sql(f"""
                CALL spark_catalog.system.expire_snapshots(
                  table           => '{fqn}',
                  older_than      => TIMESTAMP '{cutoff_ts.strftime('%Y-%m-%d %H:%M:%S')}',
                  retain_last     => 2,
                  stream_results  => true
                )
            """)

            after_count = spark.sql(
                f"SELECT COUNT(*) AS n FROM {fqn}.snapshots"
            ).collect()[0]["n"]

            expired = max(0, before_count - after_count) if before_count >= 0 else -1
            logger.info("Expired %d snapshot(s) from %s (before=%d, after=%d)",
                        expired, fqn, before_count, after_count)
            results.append({
                "table":            fqn,
                "action":           "expired",
                "snapshots_before": before_count,
                "snapshots_after":  after_count,
                "snapshots_expired": expired,
            })

            # Also remove orphaned files (data files not referenced by any snapshot)
            spark.sql(f"""
                CALL spark_catalog.system.remove_orphan_files(
                  table      => '{fqn}',
                  older_than => TIMESTAMP '{cutoff_ts.strftime('%Y-%m-%d %H:%M:%S')}'
                )
            """)

        except Exception as e:
            logger.error("Failed to expire snapshots for %s: %s", fqn, e)
            results.append({"table": fqn, "action": "error", "error": str(e)})

# COMMAND ----------

# Emit structured summary for Databricks job output / downstream alerting
import json

print(json.dumps({
    "cutoff_timestamp": cutoff_ts.isoformat(),
    "retention_hours":  retention_hours,
    "dry_run":          dry_run,
    "tables_processed": len(results),
    "results":          results,
}, indent=2))

# COMMAND ----------

# Set notebook exit value so downstream tasks can branch on it
expired_count = sum(1 for r in results if r.get("action") == "expired")
dbutils.notebook.exit(json.dumps({"expired_tables": expired_count, "dry_run": dry_run}))
