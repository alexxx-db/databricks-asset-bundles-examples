-- =============================================================================
-- 05_register_databricks_tables.sql
-- Run as SYSADMIN
--
-- WHY: When Databricks writes an Iceberg table to S3, it generates a
-- metadata.json file (and associated manifests) but doesn't automatically
-- notify Snowflake.  To make that table visible in Snowflake, you must run
-- either:
--   a) REGISTER ICEBERG TABLE  — one-time, points at a specific metadata.json
--   b) ALTER TABLE ... REFRESH  — re-scans the metadata location for new
--      snapshots that Databricks has committed since last register/refresh
--
-- This script handles both cases, plus a helper to discover the latest
-- metadata.json path for a given table (needed for initial REGISTER).
--
-- IMPORTANT: Snowflake can only READ these tables, not write to them, because
-- the catalog writer is Databricks/UC.  Any attempt to INSERT/UPDATE in
-- Snowflake will fail with a catalog conflict error.
-- =============================================================================

USE ROLE SYSADMIN;

-- ── Register a Databricks-authored table in Snowflake ─────────────────────────
-- You need the exact S3 path to the current metadata.json.
-- Run the helper Python script (iceberg_catalog/table_migration.py:get_metadata_path)
-- or check the UC table properties:
--   SELECT table_name, location FROM iceberg_db.information_schema.tables
--   WHERE table_schema = 'finops';
-- Then: ls s3://.../metadata/ and find the latest .metadata.json file.

-- Example: Register Databricks finops.pipeline_runs in Snowflake
REGISTER ICEBERG TABLE ICEBERG_LAKEHOUSE.finops.pipeline_runs
  CATALOG           = 'ICEBERG_LAKEHOUSE'
  EXTERNAL_VOLUME   = 'ICEBERG_VOL'
  METADATA_FILE_PATH = 's3://iceberg-lakehouse/iceberg/iceberg_db/finops/pipeline_runs/metadata/00001-<uuid>.metadata.json';

-- After registering, verify Snowflake can read it
SELECT COUNT(*) FROM ICEBERG_LAKEHOUSE.finops.pipeline_runs;

-- ── Refresh a registered table after Databricks writes new snapshots ──────────
-- Run this after each Databricks job that writes to the Iceberg table.
-- In production, this should be called from a Snowflake Task or
-- triggered by the same Databricks Workflow that writes the table.

ALTER ICEBERG TABLE ICEBERG_LAKEHOUSE.finops.pipeline_runs REFRESH
  METADATA_FILE_PATH = 's3://iceberg-lakehouse/iceberg/iceberg_db/finops/pipeline_runs/metadata/00002-<uuid>.metadata.json';

-- ── Automate refresh via Snowflake Task ───────────────────────────────────────
-- This task polls for new metadata every 15 minutes.
-- In production, prefer event-driven refresh (SNS/SQS trigger from S3) over polling.

CREATE OR REPLACE TASK ICEBERG_LAKEHOUSE.finops.refresh_pipeline_runs
  WAREHOUSE = COMPUTE_WH
  SCHEDULE  = 'USING CRON */15 * * * * UTC'
  COMMENT   = 'Refresh Databricks-authored Iceberg table snapshots in Snowflake'
AS
  CALL SYSTEM$ICEBERG_REFRESH_ASYNC('ICEBERG_LAKEHOUSE.finops.pipeline_runs');

ALTER TASK ICEBERG_LAKEHOUSE.finops.refresh_pipeline_runs RESUME;
