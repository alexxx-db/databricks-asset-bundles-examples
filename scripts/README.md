# Scripts

CI and maintenance tooling for this repo. Run from the **repository root** unless noted.

## discover_bundle_dirs.py

Discovers all bundle root directories (directories containing a valid `databricks.yml` with `bundle.name`). Also validates bundle schemas when called with `--validate`.

**Requirements:** `pip install pyyaml`

**Usage:**
```bash
python scripts/discover_bundle_dirs.py              # print one dir per line
python scripts/discover_bundle_dirs.py --json        # JSON array for GitHub Actions
python scripts/discover_bundle_dirs.py --validate    # validate all databricks.yml files
python scripts/discover_bundle_dirs.py --validate -q # quiet mode (errors only)
```

---

## update_from_templates.sh

Regenerates template-generated bundle directories using `databricks bundle init`.

**Requirements:** `~/.databrickscfg` with a `[DEFAULT]` section and `host=...`.

**Usage:**
```bash
./scripts/update_from_templates.sh [CURRENT_USER_NAME]
```

---

## check_template_checksums.sh

Detects drift in template-generated directories by comparing file checksums to a recorded list.

**Usage:**
```bash
./scripts/check_template_checksums.sh           # compare against recorded checksums
./scripts/check_template_checksums.sh --update  # regenerate template_checksums.sha256
```

---

## generate_ruff_notebook_excludes.py

Finds Databricks notebook `.py` files (with `# Databricks notebook source` header) for ruff exclusion. These files use magic commands that ruff cannot parse.

**Usage:**
```bash
python scripts/generate_ruff_notebook_excludes.py          # print paths
python scripts/generate_ruff_notebook_excludes.py --toml   # print as ruff exclude array
```

---

## local_bundle_validate.sh

Validates all bundles locally with the same logic as CI (no workspace auth required).

**Usage:**
```bash
./scripts/local_bundle_validate.sh
```
