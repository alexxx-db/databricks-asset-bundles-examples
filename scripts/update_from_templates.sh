#!/usr/bin/env bash
#
# Regenerate template-generated bundle directories under the repo root.
# Requires ~/.databrickscfg with [DEFAULT] and host=...
#
# Usage:
#   ./scripts/update_from_templates.sh [CURRENT_USER_NAME]
#   CURRENT_USER_NAME: optional; if omitted, will prompt (e.g. 'lennart_kats').
#
# Set CLI_COMMAND to use a different Databricks CLI (default: databricks).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"

# Portable in-place sed: BSD (macOS) vs GNU
sed_inplace() {
  if [[ "$(uname -s)" == Darwin ]]; then
    sed -i '' "$@"
  else
    sed -i "$@"
  fi
}
export -f sed_inplace

# Restrict cleanup to text files to avoid corrupting binaries; skip .git
CLEANUP_FIND_ARGS=(
  . -type f
  -not -path '*/.git/*'
  \( -name '*.yml' -o -name '*.yaml' -o -name '*.py' -o -name '*.md'
  -o -name '*.sql' -o -name '*.sh' -o -name '*.json' -o -name '*.tf'
  -o -name '*.cfg' -o -name '*.ini' -o -name '*.toml' -o -name '*.ipynb'
  -o -name '.gitignore' -o -name '*.rst' -o -name '*.txt' \)
)

function cleanup() {
  local dir="$1"
  local bundle_uuid="$2"

  if [[ ! -d "$dir" ]]; then
    echo "Error: cleanup: directory '$dir' not found." >&2
    return 1
  fi

  pushd "$dir" >/dev/null
  # Replace workspace/user placeholders with generic values (text files only)
  find "${CLEANUP_FIND_ARGS[@]}" -exec bash -c 'sed_inplace -E "s|e2[^[:space:]]*\.com|company.databricks.com|g" "$1"' _ {} \;
  find "${CLEANUP_FIND_ARGS[@]}" -exec bash -c 'sed_inplace -E "s|[A-Za-z0-9._%+-]+@databricks\.com|user@company.com|g" "$1"' _ {} \;
  # Escape CURRENT_USER_NAME for sed (\ and &); pass via env to avoid quoting issues
  local escaped_user
  escaped_user=$(printf '%s' "${CURRENT_USER_NAME}" | sed 's/\\/\\\\/g; s/&/\\&/g')
  CURRENT_USER_ESC=$escaped_user find "${CLEANUP_FIND_ARGS[@]}" -exec bash -c 'sed_inplace -e "s|$CURRENT_USER_ESC|user_name|g" "$1"' _ {} \;
  find "${CLEANUP_FIND_ARGS[@]}" -exec bash -c 'sed_inplace -E "s|^([[:space:]]*uuid:[[:space:]]*)[^[:space:]]*[[:space:]]*$|\1'"${bundle_uuid}"'|g" "$1"' _ {} \;
  popd >/dev/null
}

function init_bundle() {
  local template_name="$1"
  local bundle_uuid="${2:-}"
  local config_json="$3"
  local cli_cmd="${CLI_COMMAND:-databricks}"

  # Extract project_name from JSON (simple grep/cut; no jq required)
  local project_name
  project_name=$(echo "$config_json" | grep -o '"project_name"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)
  if [[ -z "${project_name:-}" ]]; then
    echo "Error: could not extract project_name from config JSON." >&2
    exit 1
  fi

  echo
  echo "# $project_name"

  rm -rf "$project_name"
  local config_file
  config_file=$(mktemp)
  trap 'rm -f "$config_file"' RETURN
  echo "$config_json" > "$config_file"
  "$cli_cmd" bundle init "$template_name" --config-file "$config_file"
  cleanup "$project_name" "$bundle_uuid"
}

# --- Prereqs: ~/.databrickscfg with [DEFAULT] and host ---
if [[ ! -f ~/.databrickscfg ]]; then
  echo "Error: ~/.databrickscfg not found." >&2
  exit 1
fi

DATABRICKS_HOST=$(grep -A1 '\[DEFAULT\]' ~/.databrickscfg | grep 'host' | awk -F'=' '{print $2}' | xargs || true)
if [[ -z "${DATABRICKS_HOST:-}" ]]; then
  echo "Error: expected ~/.databrickscfg to have a [DEFAULT] section with host=..." >&2
  exit 1
fi

# --- Current user name (arg or prompt) ---
if [[ -n "${1:-}" ]]; then
  CURRENT_USER_NAME="$1"
else
  read -r -p "Enter the current user name of your 'DEFAULT' profile (e.g. 'lennart_kats'): " CURRENT_USER_NAME
  if [[ -z "${CURRENT_USER_NAME:-}" ]]; then
    echo "Error: current user name is required." >&2
    exit 1
  fi
fi

cd "$REPO_ROOT"
echo "Using Databricks CLI: ${CLI_COMMAND:-databricks}"
"${CLI_COMMAND:-databricks}" --version
echo

init_bundle "default-python" "87d5a23e-7bc7-4f52-98ee-e374b67d5681" '{
    "project_name":     "default_python",
    "include_job":      "yes",
    "include_pipeline": "yes",
    "include_python":   "yes",
    "serverless":       "yes",
    "default_catalog":  "catalog",
    "personal_schemas": "yes"
}'

init_bundle "default-sql" "853cd9bc-631c-4d4f-bca0-3195c7540854" '{
    "project_name":     "default_sql",
    "http_path":        "/sql/1.0/warehouses/abcdef1234567890",
    "default_catalog":  "catalog",
    "personal_schemas": "yes, automatically use a schema based on the current user name during development"
}'

init_bundle "dbt-sql" "5e5ca8d5-0388-473e-84a1-1414ed89c5df" '{
    "project_name":     "dbt_sql",
    "http_path":        "/sql/1.0/warehouses/abcdef1234567890",
    "serverless":       "yes",
    "default_catalog":  "catalog",
    "personal_schemas": "yes, use a schema based on the current user name during development"
}'

init_bundle "lakeflow-pipelines" "295000fc-1ea8-4f43-befe-d5fb9f7d4ad4" '{
    "project_name":     "lakeflow_pipelines_sql",
    "default_catalog":  "catalog",
    "personal_schemas": "yes",
    "language":         "sql"
}'

init_bundle "lakeflow-pipelines" "87a174ba-60e4-4867-a140-1936bc9b00de" '{
    "project_name":     "lakeflow_pipelines_python",
    "default_catalog":  "catalog",
    "personal_schemas": "yes",
    "language":         "python"
}'

init_bundle "default-minimal" "8127e9c1-adac-4c9c-b006-d3450874f663" '{
    "project_name":     "default_minimal",
    "default_catalog":  "catalog",
    "personal_schemas": "yes",
    "language_choice":  "sql"
}'

# Add minimal job and notebook to default_minimal so the bundle has one deployable resource
mkdir -p default_minimal/src default_minimal/resources
cat > default_minimal/src/minimal_notebook.py << 'MINIMAL_NB'
# Databricks notebook source
# MAGIC %md
# MAGIC Minimal notebook for the default_minimal bundle. Replace this with your own logic.

# COMMAND ----------

print("Minimal bundle job ran successfully.")
MINIMAL_NB
cat > default_minimal/resources/default_minimal_job.yml << 'MINIMAL_JOB'
# Minimal job for the default_minimal template.
resources:
  jobs:
    default_minimal_job:
      name: "default_minimal_job-${bundle.target}"
      parameters:
        - name: catalog
          default: ${var.catalog}
        - name: schema
          default: ${var.schema}
      tasks:
        - task_key: minimal_notebook
          notebook_task:
            notebook_path: ./src/minimal_notebook.py
          new_cluster:
            spark_version: "15.4.x-scala2.12"
            node_type_id: "i3.xlarge"
            num_workers: 0
            spark_conf:
              spark.databricks.cluster.profile: singleNode
              master: "local[*]"
MINIMAL_JOB

init_bundle "pydabs" "4062028b-2184-4acd-9c62-f2ec572f7843" '{
    "project_name":     "pydabs",
    "include_job":      "yes",
    "include_pipeline": "yes",
    "include_python":   "yes",
    "serverless":       "yes",
    "default_catalog":  "catalog",
    "personal_schemas": "yes"
}'
