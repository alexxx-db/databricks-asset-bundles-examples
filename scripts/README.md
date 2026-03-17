# Scripts

Canonical scripts for maintaining this repo. Run from the **repository root** unless noted.

## update_from_templates.sh

Regenerates template-generated bundle directories using `databricks bundle init`.

**Requirements:** `~/.databrickscfg` with a `[DEFAULT]` section and `host=...`.

**Usage:**
```bash
./scripts/update_from_templates.sh [CURRENT_USER_NAME]
```
- If `CURRENT_USER_NAME` is omitted, you will be prompted (e.g. `lennart_kats`).
- Set `CLI_COMMAND` to use a different Databricks CLI (default: `databricks`).

**Behavior:** Runs `bundle init` for each template, then normalizes generated files (workspace host, user, UUID) so the repo stays generic. Only touches text files (e.g. `.yml`, `.py`, `.md`) to avoid corrupting binaries. Works on macOS and Linux (portable `sed -i`).

---

## check_template_checksums.sh

Detects drift in template-generated directories by comparing file checksums to a recorded list.

**Usage:**
```bash
./scripts/check_template_checksums.sh           # compare against recorded checksums
./scripts/check_template_checksums.sh --update  # regenerate template_checksums.sha256
```
- **Advisory only** — always exits 0. Uses `sha256sum` (GNU/Linux) or `shasum -a 256` (macOS) when available.

---

## validate_bundle_schema.py

Validates that every `databricks.yml` under the repo has a `bundle.name` key. Skips paths under `contrib/templates`.

**Requirements:** `pip install pyyaml`

**Usage:**
```bash
python scripts/validate_bundle_schema.py [--quiet]
```
- **Exit 0:** all checked files valid. **Exit 1:** one or more errors (printed to stderr). **Exit 2:** missing PyYAML or invalid root.
- `--quiet`: only print errors and the final summary (no per-file OK lines).
