"""
Data format conversion utilities.
Atomic functions for converting between different data formats.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_profile_summary(table_data: dict) -> Optional[str]:
    """
    Extract profile_summary from table_data or metadata.
    Single source of truth for profile_summary lookup.

    Args:
        table_data: Table data dict with optional profile_summary or metadata.profile_summary

    Returns:
        Profile summary string or None if not found
    """
    # Check top-level first
    if 'profile_summary' in table_data:
        return table_data['profile_summary']

    # Check metadata dict
    metadata = table_data.get('metadata', {})
    if isinstance(metadata, dict):
        return metadata.get('profile_summary')

    return None


def library_yaml_to_table_data(yaml_item: dict) -> dict:
    """
    Convert library YAML item to table_data format for interview.

    Args:
        yaml_item: Library YAML item dict with keys:
            - catalog, schema, table_name
            - yaml_content, metadata, yaml_type

    Returns:
        table_data dict ready for interview with keys:
            - catalog, schema, table
            - metadata, tier1_yaml, profile_summary
    """
    table_data = {
        'catalog': yaml_item['catalog'],
        'schema': yaml_item['schema'],
        'table': yaml_item['table_name'],
        'metadata': yaml_item.get('metadata', {}),
        'tier1_yaml': yaml_item['yaml_content']  # Pre-populate from existing YAML
    }

    # Extract profile_summary using utility function
    profile_summary = get_profile_summary({'metadata': yaml_item.get('metadata', {})})
    if profile_summary:
        table_data['profile_summary'] = profile_summary

    logger.debug(f"Converted library YAML to table_data: {table_data['catalog']}.{table_data['schema']}.{table_data['table']}")
    return table_data
