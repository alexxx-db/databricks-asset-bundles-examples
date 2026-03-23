# databricks/setup/01_create_connection.py
# Run once by a metastore admin via a Databricks notebook or job
#
# WHY this order matters:
#   1. Secrets must exist before the connection is created (UC validates the secret
#      reference at CREATE CONNECTION time in some runtime versions)
#   2. The connection must exist before the foreign catalog can reference it
#   3. The external location (created by Terraform) must exist before UC can
#      use the bucket as a LOCATION for managed Iceberg tables
#
# Run with: databricks bundle run setup_connection (after adding to bundle)
# Or: attach to an interactive cluster and run cell-by-cell.


from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import (
    ConnectionType,
)

w = WorkspaceClient()

# ── Step 0: Store Polaris credentials in Databricks secrets ───────────────────
# Do this ONCE via CLI before running this notebook.
# Never hard-code credentials here.
#
# databricks secrets create-scope iceberg-polaris
# databricks secrets put-secret iceberg-polaris polaris_client_id     --string-value "<CLIENT_ID>"
# databricks secrets put-secret iceberg-polaris polaris_client_secret  --string-value "<CLIENT_SECRET>"
# databricks secrets put-secret iceberg-polaris snowflake_account      --string-value "example.us-west-2.aws"

SNOWFLAKE_ACCOUNT = dbutils.secrets.get("iceberg-polaris", "snowflake_account")  # noqa: F821
POLARIS_REST_URI  = f"https://{SNOWFLAKE_ACCOUNT}.snowflakecomputing.com/polaris/api/catalog"
TOKEN_ENDPOINT    = f"https://{SNOWFLAKE_ACCOUNT}.snowflakecomputing.com/oauth/token"
PRINCIPAL_ROLE    = "databricks_svc_role"   # must match what was created in Snowflake

# ── Step 1: Create the Iceberg REST connection ────────────────────────────────
# This is the UC object that holds the credential + endpoint for Polaris.
# All foreign catalogs pointing at this Polaris instance share one connection.

CONN_NAME = "iceberg-polaris-prod"

try:
    conn = w.connections.get(CONN_NAME)
    print(f"Connection '{CONN_NAME}' already exists — skipping creation")
except Exception:
    conn = w.connections.create(
        name=CONN_NAME,
        connection_type=ConnectionType.ICEBERG_REST,  # SDK enum
        options={
            "uri":             POLARIS_REST_URI,
            "token_endpoint":  TOKEN_ENDPOINT,
            "client_id":       "{{secrets/iceberg-polaris/polaris_client_id}}",
            "client_secret":   "{{secrets/iceberg-polaris/polaris_client_secret}}",
            "scope":           f"PRINCIPAL_ROLE:{PRINCIPAL_ROLE}",
        },
        comment="Snowflake Open Catalog (Polaris) Iceberg REST connection",
    )
    print(f"Created connection: {conn.name}  (full_name: {conn.full_name})")

# ── Step 2: Validate the connection ───────────────────────────────────────────
# UC pings the Polaris /v1/config endpoint to validate.
# If this fails with 401, the principal credentials are wrong.
# If it fails with 403, the principal role doesn't have READ_CATALOG_PROPERTIES.

try:
    validated = w.connections.get(CONN_NAME)
    print(f"Connection state: {validated.connection_type} — OK")
except Exception as e:
    raise RuntimeError(f"Connection validation failed: {e}") from e

print("\nNext step: run 02_register_catalog.py to create the foreign catalog")
