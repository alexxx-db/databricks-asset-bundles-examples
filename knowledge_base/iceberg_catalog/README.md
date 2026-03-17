# iceberg_catalog — Shared Iceberg Catalog Management

Production DABs bundle managing the shared Iceberg catalog layer between
Databricks (Unity Catalog) and Snowflake (Open Catalog / Polaris).

## Secrets

Create a Databricks secret scope (e.g. `iceberg-polaris`) and store the keys required by the jobs and notebooks. Never commit credentials to the repo. Required keys depend on your setup; typical ones include:

- `snowflake_account`, `polaris_client_id`, `polaris_client_secret` (for Polaris/Open Catalog)
- `instance_profile_arn` (for cluster S3 access)
- `slack_webhook_url` (for breaking-drift alerts; optional)

See `notebooks/01_create_connection.py` and `resources/iceberg_catalog.yml` for the exact scope and key names used. Configure the `secret_scope` variable in your bundle target or job parameters to point at your scope.

## Architecture

```
Databricks (writes)          Snowflake (reads)
     │                            │
     │  UC Managed Iceberg        │  Open Catalog (Polaris)
     │  iceberg_db                │  ICEBERG_LAKEHOUSE
     │        │                   │        │
     │        └─── S3 (Iceberg) ──┘        │
     │                            │        │
     │   ← catalog sync job ───────────────┘ (registers metadata.json)
     │   ← schema drift scan ─────────────── (detects UC ↔ Polaris divergence)
     │   ← snapshot expiry ─────────────────  (removes old S3 data files)
```

## Three jobs

| Job | Schedule | Entry point | Purpose |
|-----|----------|-------------|---------|
| `iceberg_schema_drift_scan` | 06:00 daily | `scan_drift` CLI | Detect UC ↔ Polaris schema divergence; auto-apply safe changes; alert on breaking |
| `iceberg_catalog_sync` | Every 30 min | `sync_catalog` CLI | Register/refresh Databricks tables in Snowflake after each pipeline write |
| `iceberg_snapshot_expiry` | Sunday 03:00 | Notebook | Expire snapshots >7 days; remove orphaned S3 files |

## Python wheel

The `iceberg_catalog` package contains all domain logic and is deployed as a
wheel via `python_wheel_task`. Build with:

```bash
pip install build
python -m build        # produces dist/iceberg_catalog-*.whl
databricks bundle deploy --target dev
```

Entry points (defined in `pyproject.toml`):
- `scan_drift` → `iceberg_catalog.cli:scan_drift`
- `sync_catalog` → `iceberg_catalog.cli:sync_catalog`

## Module overview

| Module | Purpose |
|--------|---------|
| `polaris_client.py` | Iceberg REST Catalog client (Snowflake Open Catalog). Token caching, retry logic, namespace + table ops |
| `schema_sync.py` | Schema drift detection: compares UC ↔ Polaris, classifies COMPATIBLE vs BREAKING, auto-applies safe changes |
| `table_migration.py` | Resolves Iceberg `metadata.json` path from UC for Snowflake REGISTER/REFRESH |
| `snowflake_refresh.py` | `ALTER ICEBERG TABLE ... REFRESH METADATA_FILE_PATH` — call at end of any pipeline that writes Iceberg |
| `cli.py` | Click CLI wrapping the above — consumed by DABs `python_wheel_task` |

## Why event-driven refresh (not Snowflake Tasks)

Snowflake Tasks poll every N minutes, wasting Snowflake credits and introducing
latency. The correct pattern:

1. Databricks pipeline writes an Iceberg snapshot to S3
2. At the end of the pipeline task, call `SnowflakeRefreshClient.refresh_table()`
3. Snowflake immediately reflects the new data — zero polling lag

```python
# Add to the end of any Databricks pipeline task that writes Iceberg:
from iceberg_catalog import SnowflakeRefreshClient, IcebergTableRegistrar
from databricks.sdk import WorkspaceClient

registrar = IcebergTableRegistrar(uc_client=WorkspaceClient(), ...)
loc = registrar.get_table_location("iceberg_db", "finops", "pipeline_runs")

refresher = SnowflakeRefreshClient.from_secrets("iceberg-polaris")
result = refresher.refresh_table(loc)
```

## Schema drift classification

| Drift kind | Safe? | Auto-applied? |
|-----------|-------|--------------|
| `COLUMN_ADDED_IN_DATABRICKS` | ✅ Yes | ✅ Yes |
| `DOC_MISMATCH` | ✅ Yes | ✅ Yes |
| `TYPE_MISMATCH` (widening: int→long) | ✅ Yes | ✅ Yes |
| `COLUMN_MISSING_IN_POLARIS` | ✅ Yes | ✅ Yes |
| `TYPE_MISMATCH` (narrowing: long→int) | ❌ Breaking | ❌ Alert only |
| `COLUMN_MISSING_IN_DATABRICKS` (required) | ❌ Breaking | ❌ Alert only |
| `NULLABILITY_MISMATCH` (optional→required) | ❌ Breaking | ❌ Alert only |

Breaking drift fires an email notification AND sends a Slack alert via
`notebooks/alert_breaking_drift.py` (conditional task in the job DAG).

## Infrastructure (Terraform)

The `terraform/` directory manages:
- S3 bucket with lifecycle rules (90-day noncurrent version expiration)
- IAM role for Databricks cluster cross-account S3 access
- IAM role for Polaris service account (Snowflake → S3 read)

```bash
terraform -chdir=terraform init
terraform -chdir=terraform apply -var-file=envs/dev.tfvars
```

## Snowflake setup (SQL scripts)

Run in order against your Snowflake account:

| Script | Purpose |
|--------|---------|
| `snowflake/01_storage_integration.sql` | Create STORAGE INTEGRATION for S3 |
| `snowflake/02_external_volume.sql` | Create EXTERNAL VOLUME pointing to S3 |
| `snowflake/03_open_catalog_setup.sql` | Create Polaris catalog + principal + role |
| `snowflake/04_iceberg_tables.sql` | Example Iceberg table DDL |
| `snowflake/05_register_databricks_tables.sql` | REGISTER ICEBERG TABLE from Databricks |

## Quick start

```bash
# 1. Apply Terraform infrastructure
terraform -chdir=terraform apply -var-file=envs/dev.tfvars

# 2. Run Snowflake setup scripts (once)
snowsql -f snowflake/01_storage_integration.sql
# ... through 05_register_databricks_tables.sql

# 3. Run Databricks one-time setup notebooks
databricks jobs run-now --notebook ./notebooks/01_create_connection.py
databricks jobs run-now --notebook ./notebooks/02_register_catalog.py

# 4. Build the Python wheel
python -m build

# 5. Deploy the bundle
databricks bundle deploy --target dev

# 6. Trigger a manual sync
databricks bundle run iceberg_catalog_sync --target dev

# 7. Test schema drift detection
databricks bundle run iceberg_schema_drift_scan --target dev
```

## Local validation

Run tests, lint, and type-check locally (no Databricks auth required):

```bash
pip install -e ".[dev]"
pytest tests/ -v --tb=short   # 24 tests
ruff check src/ tests/
mypy src/
```

Validate the bundle (requires [Databricks auth](https://docs.databricks.com/en/dev-tools/auth.html) for the target workspace):

```bash
databricks bundle validate -t dev
```

## File layout

```
iceberg_catalog/
├── databricks.yml
├── pyproject.toml                           # Package + CLI entry points
├── pytest.ini
├── resources/
│   └── iceberg_catalog.yml                 # 3 jobs: drift scan, sync, expiry
├── src/iceberg_catalog/
│   ├── __init__.py                          # Public API
│   ├── cli.py                               # Click CLI (scan_drift, sync_catalog)
│   ├── polaris_client.py                    # Iceberg REST client for Polaris
│   ├── schema_sync.py                       # Schema drift detection + classification
│   ├── table_migration.py                   # metadata.json location resolver
│   └── snowflake_refresh.py                 # ALTER ICEBERG TABLE REFRESH client
├── notebooks/
│   ├── 01_create_connection.py              # One-time: create UC connection to Polaris
│   ├── 02_register_catalog.py               # One-time: register UC foreign catalog
│   ├── expire_iceberg_snapshots.py          # Weekly snapshot expiry job
│   └── alert_breaking_drift.py             # Conditional: Slack alert on breaking drift
├── tests/
│   ├── conftest.py
│   ├── test_polaris_client.py
│   ├── test_schema_sync.py
│   └── test_table_migration.py
├── snowflake/                               # SQL setup scripts (run once)
└── terraform/                               # S3 + IAM infrastructure
    ├── main.tf, s3.tf, iam.tf, variables.tf, outputs.tf
    └── envs/{dev,prod}.tfvars
```
