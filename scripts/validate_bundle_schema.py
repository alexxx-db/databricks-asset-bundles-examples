#!/usr/bin/env python3
"""
Validate that every databricks.yml under the repo root has a bundle.name key.

Usage:
  python scripts/validate_bundle_schema.py [--quiet]
  --quiet  Only print errors and final summary (no per-file OK lines).

Exit: 0 if all valid, 1 if any errors. Skips paths under contrib/templates.
"""

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate bundle.name in every databricks.yml")
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Only print errors and summary",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    if not root.is_dir():
        print(f"Error: repo root not found: {root}", file=sys.stderr)
        sys.exit(2)

    errors: list[str] = []
    checked = 0

    for yml_path in sorted(root.rglob("databricks.yml")):
        # Skip Go-templated files in contrib/templates (OS-independent path check)
        parts = yml_path.parts
        if "contrib" in parts and "templates" in parts:
            continue

        try:
            with open(yml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except OSError as e:
            errors.append(f"{yml_path.relative_to(root)}: read error: {e}")
            continue
        except yaml.YAMLError as e:
            errors.append(f"{yml_path.relative_to(root)}: YAML parse error: {e}")
            continue

        if not isinstance(data, dict):
            errors.append(f"{yml_path.relative_to(root)}: not a YAML mapping")
            continue

        bundle = data.get("bundle")
        if not isinstance(bundle, dict) or "name" not in bundle:
            errors.append(f"{yml_path.relative_to(root)}: missing bundle.name")
            continue

        checked += 1
        if not args.quiet:
            print(f"OK: {yml_path.relative_to(root)}")

    if errors:
        print(file=sys.stderr)
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    print(f"\nAll {checked} databricks.yml file(s) valid.")


if __name__ == "__main__":
  main()
