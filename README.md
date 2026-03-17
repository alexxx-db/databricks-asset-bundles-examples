# bundle-examples

This repository provides [Databricks Asset Bundles](https://docs.databricks.com/dev-tools/bundles/index.html) examples.

## Getting started

Install the [Databricks CLI](https://docs.databricks.com/dev-tools/cli/install.html) (v0.218.0 or above) and configure authentication for your workspace.

## Repository layout

The canonical bundle examples live at the repository root (e.g. `knowledge_base/`, `default_python/`). A `scripts/` directory may contain tooling or a mirror used by some workflows; when in doubt, use paths from the root. CI discovers all bundle directories automatically via `scripts/discover_bundle_dirs.py`, so new examples are validated without updating the workflow.

## Template-generated projects

These projects were generated from the built-in `databricks bundle init` templates.
Run `scripts/update_from_templates.sh` to regenerate them.

| Directory | Description |
|-----------|-------------|
| [default_minimal](default_minimal) | Minimal project generated from the `default-minimal` template. |
| [default_python](default_python) | Python project generated from the `default-python` template. |
| [default_sql](default_sql) | SQL project generated from the `default-sql` template. |
| [dbt_sql](dbt_sql) | dbt project generated from the `dbt-sql` template. |
| [lakeflow_pipelines_python](lakeflow_pipelines_python) | LakeFlow Pipelines (Python) generated from the `lakeflow-pipelines` template. |
| [lakeflow_pipelines_sql](lakeflow_pipelines_sql) | LakeFlow Pipelines (SQL) generated from the `lakeflow-pipelines` template. |
| [mlops_stacks](mlops_stacks) | ML project based on the default Databricks MLOps Stacks. |
| [pydabs](pydabs) | Python project generated from the `pydabs` template. |

## Knowledge base examples

Standalone examples that demonstrate specific bundle features and patterns.

| Directory | Description |
|-----------|-------------|
| [alerts](knowledge_base/alerts) | Define SQL alerts using Databricks Asset Bundles. |
| [app_with_database](knowledge_base/app_with_database) | Databricks app backed by an OLTP Postgres database. |
| [dashboard_nyc_taxi](knowledge_base/dashboard_nyc_taxi) | AI/BI dashboard with a snapshot job and email subscription. |
| [database_with_catalog](knowledge_base/database_with_catalog) | OLTP database instance and database catalog. |
| [databricks_app](knowledge_base/databricks_app) | Databricks App in a bundle. |
| [development_cluster](knowledge_base/development_cluster) | Development (all-purpose) cluster in a bundle. |
| [genie_space](knowledge_base/genie_space) | Deploy a Genie space using the Management API. |
| [job_read_secret](knowledge_base/job_read_secret) | Secret scope and a job that reads from it. |
| [job_with_multiple_wheels](knowledge_base/job_with_multiple_wheels) | Job with multiple wheel dependencies. |
| [job_with_run_job_tasks](knowledge_base/job_with_run_job_tasks) | Compose multiple jobs with `run_job` tasks. |
| [job_with_sql_notebook](knowledge_base/job_with_sql_notebook) | Job that runs a SQL notebook on a SQL warehouse. |
| [pipeline_with_schema](knowledge_base/pipeline_with_schema) | Unity Catalog schema with a Delta Live Tables pipeline. |
| [private_wheel_packages](knowledge_base/private_wheel_packages) | Use a private wheel package from a job. |
| [python_wheel_poetry](knowledge_base/python_wheel_poetry) | Use Poetry with a Databricks Asset Bundle. |
| [serverless_job](knowledge_base/serverless_job) | Serverless job in a bundle. |
| [share_files_across_bundles](knowledge_base/share_files_across_bundles) | Include files located outside the bundle root directory. |
| [spark_jar_task](knowledge_base/spark_jar_task) | Spark JAR task in a bundle. |
| [target_includes](knowledge_base/target_includes) | Organize job configurations across targets with includes. |
| [write_from_job_to_volume](knowledge_base/write_from_job_to_volume) | Unity Catalog Volume in a bundle. |

## Community contributions

See the [contrib](contrib) directory for community-contributed examples and templates.

## Security and secrets

- **No credentials in the repo.** Use [Databricks secret scopes](https://docs.databricks.com/security/secrets/secret-scopes.html) or environment variables for API keys, tokens, and passwords.
- Examples that need secrets (e.g. **iceberg_catalog**, **genie_space_full**, **job_read_secret**) document the required scope and key names in their own README; create those secrets in your workspace before running jobs or apps.
- For notebooks that accept `secret_scope` / `secret_key` via widgets, ensure they point to existing secrets; tokens are never logged.

## Code quality

From the repo root you can run:

- **Linting:** `ruff check .` (config in `pyproject.toml`)
- **Type checking:** `pyright` (optional; config in `pyproject.toml`)

CI runs `yamllint`, Python syntax checks (`py_compile`), and `databricks bundle validate` for all discovered bundles.

### Running tests

- **SQL identifier validation (genie_metadata_generator):**
  ```bash
  PYTHONPATH=knowledge_base/genie_metadata_generator python -m pytest knowledge_base/genie_metadata_generator/tests/test_sql_identifiers.py -v
  ```
- **add_asset.py (contrib/data_engineering):**
  ```bash
  python -m pytest contrib/data_engineering/tests/test_add_asset.py -v
  ```
- **iceberg_catalog** (from `knowledge_base/iceberg_catalog`; requires deps):
  ```bash
  cd knowledge_base/iceberg_catalog && python -m pytest tests/ -v
  ```
- **mlops_stacks** (from bundle directory):
  ```bash
  cd mlops_stacks/mlops_stacks && python -m pytest tests/ -v
  ```

For production-like or long-lived apps, consider pinning dependency versions or using a lockfile (e.g. `pip-tools`, `poetry`) so upgrades are deliberate and reproducible.

## Learn more

* [Databricks Asset Bundles documentation](https://docs.databricks.com/dev-tools/bundles/index.html)
* [Launch blog post](https://www.databricks.com/blog/announcing-general-availability-databricks-asset-bundles)
* [Databricks CLI documentation](https://docs.databricks.com/dev-tools/cli/index.html)
