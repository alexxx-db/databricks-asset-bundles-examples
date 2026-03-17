# Databricks notebook source

# COMMAND ----------

# This notebook deploys a Genie space using the Genie Management API.
# It is invoked as a DAB job task because Genie spaces are not yet
# a native DAB resource type.

# COMMAND ----------

import json
import os

from databricks.sdk import WorkspaceClient

# COMMAND ----------

# Read job parameters passed from the DAB job definition.
warehouse_id = dbutils.widgets.get("warehouse_id")
space_title = dbutils.widgets.get("space_title")

print(f"Warehouse ID: {warehouse_id}")
print(f"Space title:  {space_title}")

# COMMAND ----------

# Construct the path to the serialized space JSON file.
# When a bundle is deployed, all files are synced to the workspace filesystem.
# The notebook's working directory is the directory containing the notebook,
# so we navigate relative to it to find the JSON config file.
# This requires DBR >= 14 or serverless compute.
notebook_dir = os.getcwd()
config_path = os.path.join(notebook_dir, "..", "genie_spaces", "sample_space.json")
config_path = os.path.normpath(config_path)

print(f"Loading space definition from: {config_path}")

with open(config_path) as f:
    serialized_space = f.read()

# Validate that the JSON is well-formed.
json.loads(serialized_space)
print("Space definition loaded and validated.")

# COMMAND ----------

# Determine the parent path for the Genie space.
# Place it in the same directory as the bundle deployment root.
parent_path = os.path.normpath(os.path.join(notebook_dir, ".."))

print(f"Parent path: {parent_path}")

# COMMAND ----------

w = WorkspaceClient()

# Check for a previously deployed space ID stored in a state file.
# The state file is stored OUTSIDE the bundle sync directory because
# `databricks bundle deploy` removes files not in the local bundle source.
existing_space_id = None
username = w.current_user.me().user_name
state_dir = f"/Workspace/Users/{username}/.genie_space_state"
os.makedirs(state_dir, exist_ok=True)
state_file = os.path.join(state_dir, f"{space_title.replace(' ', '_')}.id")

try:
    with open(state_file) as f:
        candidate_id = f.read().strip()
    if candidate_id:
        # Verify the space still exists.
        try:
            existing = w.genie.get_space(candidate_id)
            existing_space_id = candidate_id
            print(f"Found existing space from state file: {existing_space_id}")
        except Exception:
            print(f"Space ID from state file ({candidate_id}) no longer exists.")
except FileNotFoundError:
    print("No state file found. Will create a new space.")

# COMMAND ----------

if existing_space_id:
    # Update the existing space.
    print(f"Updating existing Genie space: {existing_space_id}")
    space = w.genie.update_space(
        space_id=existing_space_id,
        serialized_space=serialized_space,
        title=space_title,
        warehouse_id=warehouse_id,
    )
    print("Space updated successfully.")
else:
    # Create a new space.
    print("Creating new Genie space...")
    deploy_marker = f"[dab-managed:{space_title}]"
    space = w.genie.create_space(
        warehouse_id=warehouse_id,
        serialized_space=serialized_space,
        title=space_title,
        description=f"Managed by Databricks Asset Bundles. {deploy_marker}",
        parent_path=parent_path,
    )
    print("Space created successfully.")

    # Persist the space ID so subsequent deployments can update it.
    # This file is written to the workspace filesystem, not the local repo.
    try:
        with open(state_file, "w") as f:
            f.write(space.space_id)
        print(f"Space ID saved to state file: {state_file}")
    except Exception as e:
        print(f"Warning: Could not save state file: {e}")
        print(f"Space ID for manual tracking: {space.space_id}")

# COMMAND ----------

# Print the space URL for easy access.
workspace_host = w.config.host.rstrip("/")
space_url = f"{workspace_host}/genie/rooms/{space.space_id}"
print(f"\nGenie Space URL: {space_url}")
print(f"Space ID: {space.space_id}")
print(f"Title: {space.title}")
