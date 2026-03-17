# Genie Space with Databricks Asset Bundles

This example shows how to deploy a [Genie space](https://docs.databricks.com/en/genie/index.html) using Databricks Asset Bundles.

Genie spaces are not yet a native DAB resource type ([feature request](https://github.com/databricks/cli/issues/2340)). This example uses a DAB-managed job that calls the [Genie Management API](https://docs.databricks.com/api/workspace/genie) to programmatically create or update a Genie space at deploy time.

The sample space is configured against the `samples.nyctaxi.trips` table and includes sample questions, text instructions, and example SQL pairs.

## Prerequisites

* Databricks CLI v0.236.0 or above
* Databricks SDK for Python (pre-installed on DBR >= 14 and serverless)
* A SQL warehouse accessible to the deploying user
* The `samples.nyctaxi.trips` table (available by default on all Databricks workspaces)

## Usage

1. Modify `databricks.yml`:
   - Update the `host` field under `workspace` to your Databricks workspace URL.
   - Update the `warehouse` field under `warehouse_id` to the name of your SQL warehouse.
   - Optionally update the `space_title` variable default to your preferred space name.

2. Deploy the bundle:
   ```sh
   databricks bundle deploy
   ```

3. Run the deploy job to create or update the Genie space:
   ```sh
   databricks bundle run deploy_genie_space
   ```

   The job output will print the URL of the deployed Genie space.

4. Open the Genie space in your browser and start asking questions.

## How it works

The bundle defines a job (`deploy_genie_space`) with a single notebook task. When the job runs, the notebook:

1. Reads job parameters (`warehouse_id`, `space_title`) passed from the DAB configuration.
2. Loads the serialized space definition from `genie_spaces/sample_space.json` (synced to the workspace filesystem by `databricks bundle deploy`).
3. Checks for a previously deployed space ID in a state file (stored under `~/.genie_space_state/` in the workspace, outside the bundle sync directory).
4. Creates a new Genie space or updates the existing one via the Genie Management API.
5. Prints the space URL for easy access.

## Customizing the space definition

Edit `genie_spaces/sample_space.json` to configure:

- **`config.sample_questions`**: Suggested questions shown to users in the Genie UI.
- **`data_sources.tables`**: Tables the Genie space can query, with column descriptions.
- **`instructions.text_instructions`**: Guidance for the LLM on how to interpret questions.
- **`instructions.example_question_sqls`**: Example question-and-SQL pairs that teach the LLM your preferred query patterns.
- **`instructions.join_specs`**: Join definitions between tables (empty in this single-table example).

All IDs must be 32-character lowercase hex strings. Collections must be sorted by their ID or identifier field.

## Exporting from an existing Genie space

If you have an existing Genie space configured in the Databricks UI that you want to manage via DABs, you can export its definition:

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Replace with your space ID (from the Genie space URL: /genie/rooms/<space_id>)
space_id = "your-space-id-here"

space = w.genie.get_space(space_id, include_serialized_space=True)

# Save the serialized space to a file.
with open("genie_spaces/sample_space.json", "w") as f:
    f.write(space.serialized_space)

print(f"Exported space: {space.title}")
```

You can run this from a Databricks notebook or from your local machine with the Databricks SDK installed and authentication configured.

## Environment promotion (dev to prod)

The bundle supports `dev` and `prod` targets:

```sh
# Deploy to dev (default)
databricks bundle deploy

# Deploy to prod
databricks bundle deploy --target prod
```

In development mode (`dev` target), the job name is prefixed with `[dev <username>]` automatically. Each target deployment maintains its own Genie space instance, so dev and prod spaces are independent.

To promote a space configuration from dev to prod:

1. Iterate on `genie_spaces/sample_space.json` using the dev target.
2. When satisfied, deploy to prod: `databricks bundle deploy --target prod && databricks bundle run --target prod deploy_genie_space`.
3. The prod space will be created or updated with the same configuration.
