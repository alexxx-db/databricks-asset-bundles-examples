# Job with For Each Task

Demonstrates using a Databricks job `for_each` task to run another task in a loop over dynamically generated items.

## Prerequisites

- [Databricks CLI](https://docs.databricks.com/dev-tools/cli/install.html) v0.218.0+

## How it works

- `src/foreach/generate_items.py` — Notebook that returns a JSON list of items.
- `src/foreach/process_item.py` — Notebook that processes a single item from the list.
- `resources/for_each_task_example.job.yml` — Job definition with a `for_each` task that iterates over the generated items.

## Usage

1. Update the `workspace.host` in `databricks.yml` to your workspace URL.

2. Deploy and run:
   ```
   databricks bundle deploy --target dev
   databricks bundle run for_each_task_example
   ```

## Documentation

- [Use a For each task to run another task in a loop](https://docs.databricks.com/aws/en/jobs/for-each)
