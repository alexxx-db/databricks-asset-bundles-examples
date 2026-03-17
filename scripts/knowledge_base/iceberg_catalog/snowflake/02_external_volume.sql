-- =============================================================================
-- 02_external_volume.sql
-- Run as ACCOUNTADMIN (or SYSADMIN after grants in 01_)
--
-- WHY: An External Volume is Snowflake's pointer to the S3 location where
-- Iceberg table data + metadata lives.  This is required both for:
--   a) Snowflake-authored Iceberg tables (Snowflake writes here)
--   b) Reading Databricks-authored Iceberg tables (Snowflake reads here)
--
-- The external volume references the storage integration (which holds the
-- assumed-role credential) rather than embedding credentials directly.
-- =============================================================================

USE ROLE ACCOUNTADMIN;

-- Replace <ICEBERG_BUCKET_NAME> with terraform output iceberg_bucket_name
-- Replace <AWS_REGION>          with your AWS region (e.g. us-west-2)

CREATE OR REPLACE EXTERNAL VOLUME ICEBERG_VOL
  STORAGE_LOCATIONS = (
    (
      NAME                    = 'iceberg-primary'
      STORAGE_PROVIDER        = 'S3'
      STORAGE_AWS_ROLE_ARN    = '<SNOWFLAKE_STORAGE_ROLE_ARN>'
      STORAGE_BASE_URL        = 's3://<ICEBERG_BUCKET_NAME>/iceberg/'
      -- STORAGE_AWS_EXTERNAL_ID is taken from the integration automatically
      -- when the same role ARN is used; no need to repeat it here.
    )
  );

-- Verify the volume is connected; STATUS column should show VALID
DESCRIBE EXTERNAL VOLUME ICEBERG_VOL;

-- Grant to SYSADMIN so it can be used in Open Catalog and DDL
GRANT USAGE ON EXTERNAL VOLUME ICEBERG_VOL TO ROLE SYSADMIN;
