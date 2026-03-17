# Databricks notebook source
# notebooks/run_lakebase_migration.py
#
# Runs the Lakebase SQL migration to create the genify.user_sessions table.
#
# WHY a separate migration job:
#   The Genify app uses Lakebase (Databricks-managed PostgreSQL) as an optional
#   persistent backend so user sessions survive app restarts. The table schema
#   must be created once before the app can write sessions.
#
#   Lakebase is accessed via psycopg2. The connection parameters are provided
#   by the Databricks App runtime via environment variables injected from the
#   app's `databases:` resource block in app.yaml.
#
#   Running this as a DABs job (not inside the app) means:
#     - It executes before the app starts, not lazily on first user load
#     - It is idempotent (CREATE IF NOT EXISTS) — safe to re-run
#     - It runs as the deploy service principal, not as the app SP
#
# Prerequisites:
#   1. Lakebase instance provisioned and configured in app.yaml
#   2. LAKEBASE_HOST, LAKEBASE_PORT, LAKEBASE_DATABASE, LAKEBASE_USER,
#      LAKEBASE_PASSWORD available in the cluster environment or secret scope
#
# For dev without Lakebase: this job will log a warning and exit 0.
# The app will fall back to in-memory sessions automatically.

# COMMAND ----------

import json
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

# COMMAND ----------

dbutils.widgets.text("warehouse_id", "")
warehouse_id = dbutils.widgets.get("warehouse_id")

# COMMAND ----------

# Check whether Lakebase is configured in the environment
lakebase_host = os.environ.get("LAKEBASE_HOST", "")
lakebase_enabled = os.environ.get("LAKEBASE_ENABLED", "false").lower() in ("true", "1", "yes")

if not lakebase_enabled or not lakebase_host:
    logger.warning(
        "Lakebase is not configured (LAKEBASE_ENABLED=%s, LAKEBASE_HOST=%r). "
        "Genify will use in-memory sessions. "
        "Set lakebase_enabled=true in databricks.yml and provision a Lakebase instance "
        "to enable persistent sessions.",
        os.environ.get("LAKEBASE_ENABLED", "false"),
        lakebase_host,
    )
    dbutils.notebook.exit(json.dumps({"status": "skipped", "reason": "lakebase_not_configured"}))

# COMMAND ----------

# Read the migration SQL from the migrations directory
migration_path = Path(__file__).parent.parent / "migrations" / "001_create_sessions_table.sql"
logger.info("Loading migration from: %s", migration_path)

with open(migration_path) as f:
    migration_sql = f.read()

logger.info("Migration SQL loaded (%d bytes)", len(migration_sql))

# COMMAND ----------

# Connect to Lakebase and run the migration
try:
    import psycopg2

    conn = psycopg2.connect(
        host     = os.environ["LAKEBASE_HOST"],
        port     = int(os.environ.get("LAKEBASE_PORT", "5432")),
        dbname   = os.environ.get("LAKEBASE_DATABASE", "genify"),
        user     = os.environ["LAKEBASE_USER"],
        password = os.environ["LAKEBASE_PASSWORD"],
        connect_timeout = 30,
    )
    conn.autocommit = False

    with conn.cursor() as cur:
        cur.execute(migration_sql)
    conn.commit()
    conn.close()

    logger.info("Migration completed successfully.")
    result = {"status": "success", "migration": "001_create_sessions_table.sql"}

except ImportError:
    logger.error("psycopg2 not available. Install it in the cluster: pip install psycopg2-binary")
    raise
except KeyError as e:
    logger.error("Missing environment variable: %s", e)
    raise
except Exception as e:
    logger.error("Migration failed: %s", e)
    raise

# COMMAND ----------

print(json.dumps(result, indent=2))
dbutils.notebook.exit(json.dumps(result))
