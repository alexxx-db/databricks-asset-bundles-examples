# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # Set Genie Space Permissions
# MAGIC
# MAGIC Applies ACLs to a deployed Genie space via the REST API.
# MAGIC
# MAGIC ## Why this is needed
# MAGIC
# MAGIC Genie Space permissions are **not** manageable through DABs resource definitions.
# MAGIC The `databricks.yml` `resources.genie` key does not exist (as of CLI 0.263+).
# MAGIC The only supported path is the permissions REST API:
# MAGIC
# MAGIC ```
# MAGIC GET  /api/2.0/permissions/genie/{space_id}
# MAGIC PATCH /api/2.0/permissions/genie/{space_id}
# MAGIC ```
# MAGIC
# MAGIC **Critical:** The API slug is `genie`, NOT `genie-spaces`. Using the wrong
# MAGIC slug returns 404 with no helpful error message.
# MAGIC
# MAGIC ## Valid permission levels
# MAGIC
# MAGIC | Level        | What it grants                              |
# MAGIC |--------------|---------------------------------------------|
# MAGIC | CAN_READ     | View the space, run questions               |
# MAGIC | CAN_RUN      | Same as CAN_READ (alias)                    |
# MAGIC | CAN_EDIT     | Edit space config, add instructions         |
# MAGIC | CAN_MANAGE   | Full control including permissions grant    |
# MAGIC
# MAGIC ## Parameters
# MAGIC
# MAGIC | Parameter     | Description                                          |
# MAGIC |---------------|------------------------------------------------------|
# MAGIC | `space_id`    | 32-char hex ID of the Genie space                    |
# MAGIC | `read_groups` | Comma-separated group names to grant CAN_READ        |
# MAGIC | `manage_groups`| Comma-separated group names to grant CAN_MANAGE     |

# COMMAND ----------

import json
import os

import requests
from databricks.sdk import WorkspaceClient

# COMMAND ----------

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

space_id      = dbutils.widgets.get("space_id")
read_groups   = dbutils.widgets.get("read_groups")   # "group1,group2"
manage_groups = dbutils.widgets.get("manage_groups") # "admins"

read_list   = [g.strip() for g in read_groups.split(",")   if g.strip()]
manage_list = [g.strip() for g in manage_groups.split(",") if g.strip()]

if not space_id:
    raise ValueError(
        "space_id parameter is empty. "
        "Run deploy_genie_space first, then pass the space ID here, "
        "or set --var space_id=<id> at bundle deploy time."
    )

print(f"space_id:      {space_id}")
print(f"read_groups:   {read_list}")
print(f"manage_groups: {manage_list}")

# COMMAND ----------

# ---------------------------------------------------------------------------
# Build the access control list
#
# We PATCH with add-only semantics. To replace all ACLs use PUT instead.
# Groups are referenced by display name (not ID). The API resolves them.
# ---------------------------------------------------------------------------

acl: list[dict] = []
for group in read_list:
    acl.append({"group_name": group, "permission_level": "CAN_READ"})
for group in manage_list:
    acl.append({"group_name": group, "permission_level": "CAN_MANAGE"})

print(f"\nACL payload ({len(acl)} entries):")
for entry in acl:
    print(f"  {entry['group_name']:40s}  {entry['permission_level']}")

# COMMAND ----------

# ---------------------------------------------------------------------------
# Apply permissions via the Permissions API
#
# IMPORTANT: The correct API slug is `genie`, not `genie-spaces`.
# The permissions service maps resource type → slug, and Genie spaces
# are registered under the `genie` slug only.
# ---------------------------------------------------------------------------

w = WorkspaceClient()
workspace_host = w.config.host.rstrip("/")

# Step 1: Read current permissions (useful for audit / idempotency check)
get_url = f"{workspace_host}/api/2.0/permissions/genie/{space_id}"
headers = {
    "Authorization": f"Bearer {w.config.token}",
    "Content-Type":  "application/json",
}

print("\n--- Current permissions ---")
resp = requests.get(get_url, headers=headers, timeout=30)
resp.raise_for_status()
current = resp.json()
for entry in current.get("access_control_list", []):
    principal = (
        entry.get("group_name")
        or entry.get("user_name")
        or entry.get("service_principal_name")
        or "<unknown>"
    )
    perms = [p.get("permission_level") for p in entry.get("all_permissions", [])]
    print(f"  {principal:40s}  {perms}")

# COMMAND ----------

# Step 2: PATCH to add the new ACL entries
patch_url = f"{workspace_host}/api/2.0/permissions/genie/{space_id}"
payload   = {"access_control_list": acl}

print(f"\n--- Applying {len(acl)} ACL entries ---")
resp = requests.patch(patch_url, headers=headers, json=payload, timeout=30)
resp.raise_for_status()
updated = resp.json()

print("Updated ACL:")
for entry in updated.get("access_control_list", []):
    principal = (
        entry.get("group_name")
        or entry.get("user_name")
        or entry.get("service_principal_name")
        or "<unknown>"
    )
    perms = [p.get("permission_level") for p in entry.get("all_permissions", [])]
    print(f"  {principal:40s}  {perms}")

# COMMAND ----------

space_url = f"{workspace_host}/genie/rooms/{space_id}"
print(f"\nPermissions applied successfully.")
print(f"Space URL: {space_url}")
