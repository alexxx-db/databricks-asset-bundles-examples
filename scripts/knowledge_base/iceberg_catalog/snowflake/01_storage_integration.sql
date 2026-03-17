-- =============================================================================
-- 01_storage_integration.sql
-- Run as ACCOUNTADMIN
--
-- WHY: Snowflake needs a "Storage Integration" object to assume the AWS IAM
-- role you created in Terraform.  The integration generates a unique
-- STORAGE_AWS_IAM_USER_ARN and STORAGE_AWS_EXTERNAL_ID that you must paste
-- back into the Terraform IAM role trust policy (Phase 2 handshake).
--
-- This is separate from the Open Catalog / Polaris setup because it is a
-- Snowflake account-level object.  The External Volume (next script) then
-- references it.
-- =============================================================================

USE ROLE ACCOUNTADMIN;

-- Step 1: Create storage integration
-- Replace <SNOWFLAKE_STORAGE_ROLE_ARN> with terraform output snowflake_storage_role_arn
-- Replace <ICEBERG_BUCKET_NAME>        with terraform output iceberg_bucket_name

CREATE OR REPLACE STORAGE INTEGRATION ICEBERG_STORAGE_INT
  TYPE                      = EXTERNAL_STAGE
  STORAGE_PROVIDER          = 'S3'
  ENABLED                   = TRUE
  STORAGE_AWS_ROLE_ARN      = '<SNOWFLAKE_STORAGE_ROLE_ARN>'  -- from terraform output
  STORAGE_ALLOWED_LOCATIONS = ('s3://<ICEBERG_BUCKET_NAME>/iceberg/');

-- Step 2: Retrieve the values needed for the IAM trust policy update
DESC INTEGRATION ICEBERG_STORAGE_INT;
-- Copy STORAGE_AWS_IAM_USER_ARN  → goes into Terraform iam.tf trust Principal
-- Copy STORAGE_AWS_EXTERNAL_ID  → goes into Terraform iam.tf trust Condition ExternalId
-- Then: terraform apply (updates the trust policy)

-- Step 3: Grant usage to the role that will own Open Catalog / external volumes
GRANT USAGE ON INTEGRATION ICEBERG_STORAGE_INT TO ROLE SYSADMIN;
