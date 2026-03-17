-- =============================================================================
-- 04_iceberg_tables.sql
-- Run as SYSADMIN (or a custom Snowflake role with USAGE on the ext volume)
--
-- WHY: Snowflake-side Iceberg table creation.  Tables created here:
--   1. Land data in the shared S3 bucket at s3://.../iceberg/iceberg_lakehouse/
--   2. Register their Iceberg metadata with Polaris (Open Catalog)
--   3. Are immediately queryable from Databricks via the foreign catalog
--      (no copy, no ETL — Databricks reads the same Iceberg metadata.json)
--
-- Table locations follow the convention:
--   s3://<bucket>/iceberg/iceberg_lakehouse/<namespace>/<table>/
--
-- Iceberg tables in Snowflake use Parquet by default.  Delta is NOT used here
-- because Snowflake cannot read Delta natively.  Iceberg is the interchange.
-- =============================================================================

USE ROLE SYSADMIN;

-- ── FinOps namespace ──────────────────────────────────────────────────────────
-- These back the FinOps Genie Spaces workstream (O2/FinOps pilot).

CREATE OR REPLACE ICEBERG TABLE ICEBERG_LAKEHOUSE.finops.workspace_dbu_daily (
  workspace_id      VARCHAR(64)       NOT NULL COMMENT 'Databricks workspace identifier',
  sku               VARCHAR(128)      NOT NULL COMMENT 'DBU SKU (e.g. JOBS_COMPUTE, SQL_COMPUTE)',
  usage_date        DATE              NOT NULL COMMENT 'Calendar date of usage',
  dbus              DOUBLE            NOT NULL COMMENT 'Total DBUs consumed',
  list_cost_usd     DOUBLE                    COMMENT 'List price USD',
  contract_cost_usd DOUBLE                    COMMENT 'Contract price USD after discounts',
  tags              VARIANT                   COMMENT 'JSON map of cluster/job tags',
  ingested_at       TIMESTAMP_NTZ             COMMENT 'Pipeline ingest timestamp'
)
  CATALOG         = 'ICEBERG_LAKEHOUSE'
  EXTERNAL_VOLUME = 'ICEBERG_VOL'
  BASE_LOCATION   = 'finops/workspace_dbu_daily/'
  COMMENT         = 'Daily DBU consumption per workspace — source: Databricks system.billing.usage';

CREATE OR REPLACE ICEBERG TABLE ICEBERG_LAKEHOUSE.finops.sql_warehouse_spend (
  warehouse_id   VARCHAR(64)   NOT NULL COMMENT 'Serverless SQL warehouse ID',
  warehouse_name VARCHAR(256)           COMMENT 'Human-readable warehouse name',
  owner_email    VARCHAR(256)           COMMENT 'Workspace-level owner',
  team_tag       VARCHAR(128)           COMMENT 'Cost-allocation team tag',
  spend_date     DATE          NOT NULL,
  dbus           DOUBLE        NOT NULL,
  list_cost_usd  DOUBLE,
  alert_breach   BOOLEAN       NOT NULL DEFAULT FALSE COMMENT 'True if monthly budget threshold exceeded'
)
  CATALOG         = 'ICEBERG_LAKEHOUSE'
  EXTERNAL_VOLUME = 'ICEBERG_VOL'
  BASE_LOCATION   = 'finops/sql_warehouse_spend/'
  COMMENT         = 'SQL warehouse spend with cost-governance alert flag';

-- ── Subscriber namespace ──────────────────────────────────────────────────────

CREATE OR REPLACE ICEBERG TABLE ICEBERG_LAKEHOUSE.subscriber.subscriber_events (
  event_id          VARCHAR(64)   NOT NULL COMMENT 'UUID for the event',
  subscriber_id     VARCHAR(64)   NOT NULL COMMENT 'DISH subscriber ID',
  event_type        VARCHAR(64)   NOT NULL COMMENT 'e.g. ACTIVATION, CHURN, UPGRADE',
  event_ts          TIMESTAMP_NTZ NOT NULL COMMENT 'Event timestamp (UTC)',
  product_code      VARCHAR(64)            COMMENT 'Product/package code',
  channel           VARCHAR(32)            COMMENT 'Acquisition/churn channel',
  region            VARCHAR(32)            COMMENT 'Geographic region',
  raw_payload       VARIANT                COMMENT 'Original event JSON payload'
)
  CATALOG         = 'ICEBERG_LAKEHOUSE'
  EXTERNAL_VOLUME = 'ICEBERG_VOL'
  BASE_LOCATION   = 'subscriber/subscriber_events/'
  CLUSTER BY (event_type, CAST(event_ts AS DATE))
  COMMENT         = 'Subscriber lifecycle events (activation, churn, upgrade)';

-- ── Billing namespace ─────────────────────────────────────────────────────────

CREATE OR REPLACE ICEBERG TABLE ICEBERG_LAKEHOUSE.billing.invoice_line_items (
  invoice_id    VARCHAR(64)      NOT NULL,
  subscriber_id VARCHAR(64)      NOT NULL,
  line_seq      INTEGER          NOT NULL,
  charge_code   VARCHAR(64)               COMMENT 'Internal charge code',
  description   VARCHAR(512),
  amount_usd    DECIMAL(12, 4)   NOT NULL,
  tax_usd       DECIMAL(12, 4),
  billing_period_start DATE      NOT NULL,
  billing_period_end   DATE      NOT NULL,
  created_at    TIMESTAMP_NTZ    NOT NULL
)
  CATALOG         = 'ICEBERG_LAKEHOUSE'
  EXTERNAL_VOLUME = 'ICEBERG_VOL'
  BASE_LOCATION   = 'billing/invoice_line_items/'
  CLUSTER BY (billing_period_start, subscriber_id)
  COMMENT         = 'Invoice line items — source: Billing system of record';

-- ── Verification ──────────────────────────────────────────────────────────────
SHOW ICEBERG TABLES IN SCHEMA ICEBERG_LAKEHOUSE.finops;
SHOW ICEBERG TABLES IN SCHEMA ICEBERG_LAKEHOUSE.subscriber;
SHOW ICEBERG TABLES IN SCHEMA ICEBERG_LAKEHOUSE.billing;

-- Confirm the table is visible in the Polaris catalog (Open Catalog tab in Snowsight)
-- and verify the METADATA_LOCATION column points to the correct S3 path.
SELECT SYSTEM$GET_ICEBERG_TABLE_INFORMATION('ICEBERG_LAKEHOUSE.finops.workspace_dbu_daily');
