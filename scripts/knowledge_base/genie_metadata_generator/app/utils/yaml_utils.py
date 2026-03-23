"""
YAML validation and manipulation utilities.
Atomic functions for YAML operations across the app.
"""
import yaml
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def validate_yaml(yaml_content: str) -> Tuple[bool, Optional[str]]:
    """
    Atomic YAML validation function.

    Args:
        yaml_content: YAML string to validate

    Returns:
        (is_valid: bool, error: Optional[str])
    """
    try:
        yaml.safe_load(yaml_content)
        return (True, None)
    except yaml.YAMLError as e:
        error_msg = str(e)
        logger.debug(f"YAML validation failed: {error_msg}")
        return (False, error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"YAML validation error: {error_msg}", exc_info=True)
        return (False, error_msg)
