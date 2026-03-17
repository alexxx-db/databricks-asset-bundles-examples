#!/usr/bin/env bash
#
# Validate all bundle directories locally (same logic as CI).
# No workspace auth required: uses placeholder host for config-only validation.
#
# Usage:
#   ./scripts/local_bundle_validate.sh
#   DATABRICKS_HOST=https://placeholder.databricks.com ./scripts/local_bundle_validate.sh
#
# Requires: python with pyyaml, databricks CLI
# Exit: 0 if all bundles validate; 1 on first failure.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
cd "$REPO_ROOT"

export DATABRICKS_HOST="${DATABRICKS_HOST:-https://placeholder.databricks.com}"

if ! command -v databricks &>/dev/null; then
  echo "Error: databricks CLI not found. Install it and ensure it is on PATH." >&2
  exit 1
fi

python scripts/discover_bundle_dirs.py >/dev/null || {
  echo "Error: discover_bundle_dirs.py failed (no valid bundles?)." >&2
  exit 1
}

for dir in $(python scripts/discover_bundle_dirs.py); do
  echo "Validating $dir ..."
  (cd "$dir" && databricks bundle validate -t dev) || exit 1
done

echo "All bundles validated successfully."
