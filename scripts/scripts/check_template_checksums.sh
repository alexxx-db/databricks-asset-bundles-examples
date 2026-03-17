#!/usr/bin/env bash
#
# Detect drift in template-generated directories.
#
# Usage:
#   ./scripts/check_template_checksums.sh           # compare against recorded checksums
#   ./scripts/check_template_checksums.sh --update   # regenerate checksums file
#
# Advisory only — always exits 0.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHECKSUM_FILE="$REPO_ROOT/scripts/template_checksums.sha256"

TEMPLATE_DIRS=(
  default_python
  default_sql
  dbt_sql
  lakeflow_pipelines_sql
  lakeflow_pipelines_python
  default_minimal
  pydabs
  mlops_stacks
)

generate_checksums() {
  cd "$REPO_ROOT"
  for dir in "${TEMPLATE_DIRS[@]}"; do
    if [ -d "$dir" ]; then
      find "$dir" -type f -not -path '*/.git/*' -print0 | sort -z | xargs -0 sha256sum
    fi
  done
}

if [ "${1:-}" = "--update" ]; then
  generate_checksums > "$CHECKSUM_FILE"
  echo "Checksums updated: $CHECKSUM_FILE"
  exit 0
fi

if [ ! -f "$CHECKSUM_FILE" ]; then
  echo "No checksum file found at $CHECKSUM_FILE"
  echo "Run with --update to generate it."
  exit 0
fi

echo "Checking template-generated directories for drift..."
cd "$REPO_ROOT"
if sha256sum --check --quiet "$CHECKSUM_FILE" 2>/dev/null; then
  echo "OK: All template-generated directories match recorded checksums."
else
  echo ""
  echo "DRIFT DETECTED: Some template-generated files have changed."
  echo "This is advisory only. If the change is intentional, run:"
  echo "  ./scripts/check_template_checksums.sh --update"
  echo ""
  sha256sum --check "$CHECKSUM_FILE" 2>&1 | grep -v ': OK$' || true
fi

exit 0
