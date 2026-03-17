#!/usr/bin/env python3
"""
Discover all bundle root directories (directories containing a valid databricks.yml with bundle.name).
Used by CI to validate all bundles without maintaining a static matrix.
Skips paths under contrib/templates (Go-templated files).

Usage:
  python scripts/discover_bundle_dirs.py           # print one dir per line (relative to repo root)
  python scripts/discover_bundle_dirs.py --json   # print JSON array for GitHub Actions

Exit: 0 with list to stdout; 1 if no valid bundles or on error.
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


def discover_bundle_dirs(root: Path) -> list[str]:
    """Return sorted list of relative paths to bundle root directories."""
    dirs = []
    for yml_path in sorted(root.rglob("databricks.yml")):
        parts = yml_path.parts
        if "contrib" in parts and "templates" in parts:
            continue
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
        # Bundle root is the directory containing databricks.yml
        bundle_dir = yml_path.parent.relative_to(root)
        dirs.append(str(bundle_dir))
    return sorted(set(dirs))


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover bundle root directories")
    parser.add_argument("--json", action="store_true", help="Output JSON array")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    if not root.is_dir():
        print("Error: repo root not found", file=sys.stderr)
        sys.exit(2)

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
