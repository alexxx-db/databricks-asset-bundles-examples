#!/usr/bin/env python3
"""Validate that every databricks.yml has a bundle.name key."""

import sys
from pathlib import Path

import yaml


def main():
    root = Path(__file__).resolve().parent.parent
    errors = []

    for yml_path in sorted(root.rglob("databricks.yml")):
        # Skip Go-templated files in contrib/templates
        if "contrib/templates" in str(yml_path):
            continue

        try:
            with open(yml_path) as f:
                data = yaml.safe_load(f)
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

        print(f"OK: {yml_path.relative_to(root)}")

    if errors:
        print()
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    print(f"\nAll databricks.yml files valid.")


if __name__ == "__main__":
    main()
