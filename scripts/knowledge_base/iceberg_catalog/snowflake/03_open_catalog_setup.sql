-- =============================================================================
-- 03_open_catalog_setup.sql
-- Run as ORGADMIN or ACCOUNTADMIN (Polaris/Open Catalog operations)
--
-- WHY: Snowflake Open Catalog is the Iceberg REST Catalog server.  It is a
-- separate service within the Snowflake account (accessed via the Polaris API
-- endpoint) but administered through Snowflake SQL.
--
-- Databricks will connect to Polaris using an OAuth2 client_credentials flow
-- with the service principal credentials created here.  The principal is
-- granted a role in the Polaris catalog, which scopes what it can read/write.
--
-- Polaris object model:
--   Catalog                 ← top-level namespace (maps 1:1 to a UC foreign catalog)
--     Namespace (schema)
--       Table               ← Iceberg table (metadata.json pointer)
--   CatalogRole             ← fine-grained permissions within a catalog
--   Principal               ← service account for programmatic access
--   PrincipalRole           ← account-level role granted to a principal
-- =============================================================================

USE ROLE ORGADMIN;   -- or ACCOUNTADMIN if ORGADMIN is not available

-- ── Step 1: Create the Polaris catalog ────────────────────────────────────────
-- The catalog name becomes the value passed in the Databricks CREATE FOREIGN
-- CATALOG ... OPTIONS (warehouse '<CATALOG_NAME>').

CREATE OR REPLACE CATALOG ICEBERG_LAKEHOUSE
  STORAGE_ROOT = 's3://<ICEBERG_BUCKET_NAME>/iceberg/iceberg_lakehouse'
  EXTERNAL_VOLUME = 'ICEBERG_VOL';
-- Note: STORAGE_ROOT is where this catalog's table data lands by default.
-- Individual tables can override with a table-level location.

-- ── Step 2: Create namespaces (map to Databricks schemas) ────────────────────
USE CATALOG ICEBERG_LAKEHOUSE;

CREATE NAMESPACE billing;
CREATE NAMESPACE subscriber;
CREATE NAMESPACE finops;
CREATE NAMESPACE media_ops;

-- ── Step 3: Create catalog roles ──────────────────────────────────────────────
-- Polaris catalog roles control read/write on specific resources within the
-- catalog.  We create two: one for full admin (for the Databricks svc account)
-- and one read-only (for downstream consumers who only need SELECT).

CREATE CATALOG ROLE ICEBERG_LAKEHOUSE.databricks_admin;
CREATE CATALOG ROLE ICEBERG_LAKEHOUSE.reader;

-- Grant catalog-level privileges to databricks_admin
GRANT CATALOG ROLE ICEBERG_LAKEHOUSE.databricks_admin PRIVILEGES
  READ_CATALOG_PROPERTIES,
  WRITE_CATALOG_PROPERTIES,
  CREATE_NAMESPACE,
  READ_NAMESPACE,
  UPDATE_NAMESPACE,
  DROP_NAMESPACE,
  LIST_NAMESPACES,
  LIST_TABLES,
  CREATE_TABLE,
  READ_TABLE_PROPERTIES,
  WRITE_TABLE_PROPERTIES,
  DROP_TABLE,
  LOAD_TABLE,
  COMMIT_TABLE_METADATA;

-- Read-only role gets subset
GRANT CATALOG ROLE ICEBERG_LAKEHOUSE.reader PRIVILEGES
  READ_CATALOG_PROPERTIES,
  READ_NAMESPACE,
  LIST_NAMESPACES,
  LIST_TABLES,
  READ_TABLE_PROPERTIES,
  LOAD_TABLE;

-- ── Step 4: Create a Polaris principal (service account) ──────────────────────
-- The principal is used by Databricks for OAuth2 client_credentials auth.
-- After creation, Snowflake returns a CLIENT_ID and CLIENT_SECRET — save them
-- immediately; the secret is only shown once.

CREATE PRINCIPAL databricks_svc
  TYPE SERVICE;
-- IMPORTANT: After this statement succeeds, immediately copy:
--   CLIENT_ID     → store in Databricks secret scope as 'polaris_client_id'
--   CLIENT_SECRET → store in Databricks secret scope as 'polaris_client_secret'

-- ── Step 5: Create a principal role and link it to the catalog role ───────────
-- Principal roles are account-level; catalog roles are catalog-scoped.
-- A principal is granted a principal role, and that principal role is granted
-- catalog roles within specific catalogs.

CREATE PRINCIPAL ROLE databricks_svc_role;

-- Assign the principal to the principal role
GRANT PRINCIPAL ROLE databricks_svc_role TO PRINCIPAL databricks_svc;

-- Assign the principal role to the catalog's admin role
GRANT CATALOG ROLE ICEBERG_LAKEHOUSE.databricks_admin
  TO PRINCIPAL ROLE databricks_svc_role;

-- ── Step 6: Verify ─────────────────────────────────────────────────────────────
SHOW CATALOGS;
SHOW PRINCIPAL ROLES;
SHOW PRINCIPALS IN PRINCIPAL ROLE databricks_svc_role;

-- The OAuth token endpoint that Databricks will call:
--   https://<SNOWFLAKE_ACCOUNT>.snowflakecomputing.com/oauth/token
--   scope = 'PRINCIPAL_ROLE:databricks_svc_role'
--
-- The Iceberg REST Catalog base URI:
--   https://<SNOWFLAKE_ACCOUNT>.snowflakecomputing.com/polaris/api/catalog
