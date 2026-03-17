#!/usr/bin/env bash
#
# Detect drift in template-generated directories.
#
# Usage:
#   ./scripts/check_template_checksums.sh           # compare against recorded checksums
#   ./scripts/check_template_checksums.sh --update # regenerate checksums file
#
# Portable: uses sha256sum (GNU/Linux) or shasum -a 256 (macOS). Advisory only — exits 0.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
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

# Prefer sha256sum (GNU); fall back to shasum -a 256 (macOS/BSD). Same output format: "hash  path"
if command -v sha256sum &>/dev/null; then
  SHA256_GEN() { sha256sum "$@"; }
  SHA256_CHECK_QUIET() { sha256sum --check --quiet "$1"; }
  SHA256_CHECK_VERBOSE() { sha256sum --check "$1"; }
elif command -v shasum &>/dev/null; then
  SHA256_GEN() { shasum -a 256 "$@"; }
  SHA256_CHECK_QUIET() { shasum -a 256 -c "$1" >/dev/null 2>&1; }
  SHA256_CHECK_VERBOSE() { shasum -a 256 -c "$1"; }
else
  echo "Error: need sha256sum or shasum in PATH." >&2
  exit 1
fi

generate_checksums() {
  cd "$REPO_ROOT"
  for dir in "${TEMPLATE_DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
      find "$dir" -type f -not -path '*/.git/*' -print0 | sort -z | xargs -0 SHA256_GEN
    fi
  done
}

if [[ "${1:-}" = "--update" ]]; then
  generate_checksums > "$CHECKSUM_FILE"
  echo "Checksums updated: $CHECKSUM_FILE"
  exit 0
fi

if [[ ! -f "$CHECKSUM_FILE" ]]; then
  echo "No checksum file found at $CHECKSUM_FILE"
  echo "Run with --update to generate it (from a machine with template dirs present)."
  exit 0
fi

echo "Checking template-generated directories for drift..."
cd "$REPO_ROOT"
if SHA256_CHECK_QUIET "$CHECKSUM_FILE"; then
  echo "OK: All template-generated directories match recorded checksums."
else
  echo ""
  echo "DRIFT DETECTED: Some template-generated files have changed."
  echo "Advisory only. If the change is intentional, run:"
  echo "  ./scripts/check_template_checksums.sh --update"
  echo ""
  SHA256_CHECK_VERBOSE "$CHECKSUM_FILE" 2>&1 | grep -v ': OK$' || true
fi

exit 0
