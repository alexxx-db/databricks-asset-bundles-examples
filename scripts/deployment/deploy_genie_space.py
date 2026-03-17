import json
import logging
import os
import sys
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import ApiError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("deploy_genie_space")

def load_config(file_path: str) -> dict:
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load Genie Space config: {e}")
        sys.exit(1)

def find_existing_space(w: WorkspaceClient, title: str):
    try:
        spaces = w.genie.list_spaces()
        for space in spaces:
            if getattr(space, "title", None) == title:
                return space
    except Exception as e:
        logger.error(f"Error listing Genie Spaces: {e}")
        return None
    return None

def main():
    # Use environment variables for parameterization (recommended for jobs/wheels/production)
    config_path = os.environ.get("GENIE_SPACE_CONFIG_PATH", "genie_spaces/billing_assistant.json")
    warehouse_id = os.environ.get("WAREHOUSE_ID")
    target_catalog = os.environ.get("TARGET_CATALOG")  # Unused, but ready for future

    if not warehouse_id:
        logger.error("WAREHOUSE_ID environment variable must be set.")
        sys.exit(1)
    logger.info(f"Using Genie Space config at {config_path}")

    w = WorkspaceClient()

    genie_config = load_config(config_path)
    genie_config["warehouse_id"] = warehouse_id

    logger.info(f"Beginning deployment for Genie Space: {genie_config.get('title')}")

    existing = find_existing_space(w, genie_config.get("title"))
    try:
        if existing:
            w.genie.update_space(space_id=existing.space_id, **genie_config)
            logger.info(f"Genie Space '{genie_config['title']}' updated successfully (space_id={existing.space_id}).")
        else:
            w.genie.create_space(**genie_config)
            logger.info(f"Genie Space '{genie_config['title']}' created successfully.")
    except ApiError as e:
        logger.error(f"Genie Space deployment failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()