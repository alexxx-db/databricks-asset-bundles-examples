# Job with SQL notebook

This example demonstrates how to define a Databricks Asset Bundle with a job that runs a SQL notebook on a SQL warehouse.

The included notebook executes a simple `select * from range(10)` query.

For more information, please refer to the [documentation](https://docs.databricks.com/en/workflows/jobs/how-to/use-bundles-with-jobs.html).

## Prerequisites

* Databricks CLI v0.218.0 or above

## Usage

Modify `databricks.yml`:
* Update the `host` field under `workspace` to the Databricks workspace to deploy to.
* Update the `warehouse_id` field to the ID of the SQL warehouse to use.

Run `databricks bundle deploy` to deploy the job.

Run `databricks bundle run job_with_sql_notebook` to run the job.
