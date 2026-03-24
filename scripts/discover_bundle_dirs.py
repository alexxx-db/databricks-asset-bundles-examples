#!/usr/bin/env python3
"""
Discover all bundle root directories (directories containing a valid databricks.yml with bundle.name).
Used by CI to validate all bundles without maintaining a static matrix.
Skips paths under contrib/templates (Go-templated files).

Usage:
  python scripts/discover_bundle_dirs.py              # print one dir per line (relative to repo root)
  python scripts/discover_bundle_dirs.py --json        # print JSON array for GitHub Actions
  python scripts/discover_bundle_dirs.py --validate    # validate all databricks.yml and report errors

Exit: 0 with list to stdout; 1 if no valid bundles, validation errors, or on error.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


def _iter_bundle_ymls(root: Path):
    """Yield (yml_path, relative_path) for every databricks.yml, skipping contrib/templates."""
    for yml_path in sorted(root.rglob("databricks.yml")):
        parts = yml_path.parts
        if "contrib" in parts and "templates" in parts:
            continue
        yield yml_path, yml_path.relative_to(root)


def discover_bundle_dirs(root: Path) -> list[str]:
    """Return sorted list of relative paths to bundle root directories."""
    dirs = []
    for yml_path, _rel in _iter_bundle_ymls(root):
        try:
            with open(yml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(data, dict):
            continue
        bundle = data.get("bundle")
        if not isinstance(bundle, dict) or "name" not in bundle:
            continue
        bundle_dir = yml_path.parent.relative_to(root)
        dirs.append(str(bundle_dir))
    return sorted(set(dirs))


def validate_bundle_schemas(root: Path, *, quiet: bool = False) -> bool:
    """Validate that every databricks.yml has a bundle.name key. Returns True if all valid."""
    errors: list[str] = []
    checked = 0

    for yml_path, rel_path in _iter_bundle_ymls(root):
        try:
            with open(yml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except OSError as e:
            errors.append(f"{rel_path}: read error: {e}")
            continue
        except yaml.YAMLError as e:
            errors.append(f"{rel_path}: YAML parse error: {e}")
            continue

        if not isinstance(data, dict):
            errors.append(f"{rel_path}: not a YAML mapping")
            continue

        bundle = data.get("bundle")
        if not isinstance(bundle, dict) or "name" not in bundle:
            errors.append(f"{rel_path}: missing bundle.name")
            continue

        checked += 1
        if not quiet:
            print(f"OK: {rel_path}")

    if errors:
        print(file=sys.stderr)
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return False

    print(f"\nAll {checked} databricks.yml file(s) valid.")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover and validate bundle root directories")
    parser.add_argument("--json", action="store_true", help="Output JSON array")
    parser.add_argument("--validate", action="store_true", help="Validate all databricks.yml files")
    parser.add_argument("-q", "--quiet", action="store_true", help="Only print errors and summary (with --validate)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    if not root.is_dir():
        print("Error: repo root not found", file=sys.stderr)
        sys.exit(2)

    if args.validate:
        ok = validate_bundle_schemas(root, quiet=args.quiet)
        sys.exit(0 if ok else 1)

    dirs = discover_bundle_dirs(root)
    if not dirs:
        print("Error: no valid bundle directories found", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(dirs))
    else:
        for d in dirs:
            print(d)


if __name__ == "__main__":
    main()
