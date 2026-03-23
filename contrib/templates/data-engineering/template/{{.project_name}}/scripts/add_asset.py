#!/usr/bin/env python3
#
# add_asset.py is used to initialize a new asset from the data-engineering template.
#
import shutil
import subprocess
import sys
from typing import List, Literal

VALID_ASSETS = ["etl-pipeline", "job", "ingest-pipeline"]
AssetType = Literal["etl-pipeline", "job", "ingest-pipeline"]

# Options that may be passed through to `databricks bundle init` (option, requires_value)
ALLOWED_PASSTHROUGH = frozenset({"--config", "--target"})


def _parse_passthrough_args(args: List[str]) -> List[str]:
    """Parse argv for allowlisted options and their values. Prevents command injection."""
    result = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ALLOWED_PASSTHROUGH:
            result.append(arg)
            i += 1
            if i < len(args) and not args[i].startswith("-"):
                result.append(args[i])
                i += 1
        else:
            i += 1
    return result


def init_bundle(asset_type: AssetType) -> None:
    databricks = shutil.which("databricks") or "databricks"
    template_dir = f"contrib/templates/data-engineering/assets/{asset_type}"
    cmd = [
        databricks,
        "bundle",
        "init",
        "https://github.com/databricks/bundle-examples",
        "--template-dir",
        template_dir,
    ]
    cmd.extend(_parse_passthrough_args(sys.argv[2:]))
    subprocess.run(cmd, shell=False)


def show_menu() -> AssetType:
    print("\nSelect asset type to initialize:")
    for i, asset in enumerate(VALID_ASSETS, 1):
        print(f"{i}. {asset}")

    while True:
        try:
            choice = int(input("\nEnter number (1-3): "))
            if 1 <= choice <= len(VALID_ASSETS):
                return VALID_ASSETS[choice - 1]
            print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a number.")


def main() -> None:
    if len(sys.argv) > 1:
        asset_type = sys.argv[1]
        if asset_type not in VALID_ASSETS:
            print(f"Error: Asset type must be one of {VALID_ASSETS}")
            sys.exit(1)
    else:
        asset_type = show_menu()

    init_bundle(asset_type)


if __name__ == "__main__":
    main()
