# databricks/setup/02_register_catalog.py
# Run after 01_create_connection.py, by a metastore admin.
#
# WHY a foreign catalog vs. a managed catalog:
#   A FOREIGN catalog is a *proxy* into an external catalog service (Polaris).
#   UC does not own the data; it cannot DROP tables through this catalog.
#   A MANAGED Iceberg catalog (CREATE CATALOG ... USING CONNECTION ...) would
#   let UC own and create Iceberg tables on the shared S3 bucket — that's for
#   Databricks-authored tables.  Here we register both patterns:
#     - iceberg_sf  → FOREIGN (proxy to Polaris, Snowflake-managed tables)
#     - iceberg_db  → MANAGED (Databricks-authored Iceberg on same S3)

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

CONN_NAME           = "iceberg-polaris-prod"
POLARIS_CATALOG     = "ICEBERG_LAKEHOUSE"   # must match CREATE CATALOG in Snowflake
EXTERNAL_LOC_NAME   = "iceberg-root-prod"   # from terraform output

# ── Part A: Foreign catalog (Snowflake-side tables, read + write via Polaris) ─
FOREIGN_CATALOG = "iceberg_sf"

try:
    c = w.catalogs.get(FOREIGN_CATALOG)
    print(f"Foreign catalog '{FOREIGN_CATALOG}' already exists")
except Exception:
    c = w.catalogs.create(
        name=FOREIGN_CATALOG,
        connection_name=CONN_NAME,
        options={
            # "warehouse" tells Polaris which catalog to map into.
            # This must exactly match the Polaris catalog name (case-sensitive).
            "warehouse": POLARIS_CATALOG,
        },
        comment="Foreign catalog: Snowflake Iceberg tables via Polaris REST",
    )
    print(f"Created foreign catalog: {c.full_name}")

# ── Part B: Managed Iceberg catalog (Databricks-authored tables, same S3) ─────
# Databricks writes Iceberg metadata to S3 and registers it in a UC-managed
# catalog.  Snowflake can then read these tables by pointing its external volume
# at the same S3 paths and running REGISTER ICEBERG TABLE.

DB_ICEBERG_CATALOG = "iceberg_db"

try:
    c2 = w.catalogs.get(DB_ICEBERG_CATALOG)
    print(f"Managed Iceberg catalog '{DB_ICEBERG_CATALOG}' already exists")
except Exception:
    c2 = w.catalogs.create(
        name=DB_ICEBERG_CATALOG,
        storage_root="s3://iceberg-lakehouse/iceberg/iceberg_db",
        comment="Managed Iceberg catalog: Databricks-authored tables, readable by Snowflake",
    )
    print(f"Created managed Iceberg catalog: {c2.full_name}")

# ── Part C: Grant permissions ──────────────────────────────────────────────────
# Grant USE CATALOG + USE SCHEMA + SELECT on the foreign catalog to the
# data platform group so Genie Spaces and SQL warehouses can query Snowflake tables.

DATA_PLATFORM_GROUP = "data-platform-engineers"
GENIE_SERVICE_PRINCIPAL = "genie-spaces-sp"   # adjust to your UC SP name

for catalog_name in [FOREIGN_CATALOG, DB_ICEBERG_CATALOG]:
    w.grants.update(
        securable_type="CATALOG",
        full_name=catalog_name,
        changes=[
            {
                "principal": DATA_PLATFORM_GROUP,
                "add": ["USE CATALOG", "USE SCHEMA", "SELECT"],
            },
            {
                "principal": GENIE_SERVICE_PRINCIPAL,
                "add": ["USE CATALOG", "USE SCHEMA", "SELECT"],
            },
        ],
    )
    print(f"Granted USE/SELECT on {catalog_name} to {DATA_PLATFORM_GROUP} and {GENIE_SERVICE_PRINCIPAL}")

print("""
Done.  You can now query Snowflake Iceberg tables from Databricks:

  SELECT * FROM iceberg_sf.finops.workspace_dbu_daily LIMIT 10;
  SELECT * FROM iceberg_sf.subscriber.subscriber_events LIMIT 10;

And create Iceberg tables from Databricks that Snowflake can read:

  CREATE TABLE iceberg_db.finops.pipeline_runs
  USING ICEBERG
  TBLPROPERTIES ('write.format.default' = 'parquet')
  AS SELECT ...;

Then register in Snowflake (see 05_register_databricks_tables.sql).
""")
