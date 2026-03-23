"""
Library service for YAML library operations.

Handles all library operations with graceful degradation when
Lakebase is unavailable.
"""
import logging
from functools import wraps
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from ..persistence import PersistenceService

logger = logging.getLogger(__name__)


def _with_availability_check(default_return):
    """
    Decorator for methods requiring Lakebase availability.
    Handles availability check and error logging automatically.

    Args:
        default_return: Value to return if unavailable or on error
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not self.is_available():
                return default_return
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                return default_return
        return wrapper
    return decorator


class LibraryService:
    """
    Service for YAML library operations.

    Gracefully handles Lakebase unavailability by returning empty
    results instead of raising exceptions.
    """

    def __init__(self, persistence_service: Optional['PersistenceService']):
        """
        Initialize library service.

        Args:
            persistence_service: PersistenceService instance or None if unavailable
        """
        self.persistence = persistence_service

    def is_available(self) -> bool:
        """Check if library service is available (Lakebase connected)."""
        return self.persistence is not None

    def save_yamls(
        self,
        completed_tables: List[Dict],
        genie_yaml: Optional[str] = None,
        skip_genie: bool = False,
        tags: Optional[List[str]] = None
    ) -> int:
        """
        Save YAMLs to library (orchestrator method).

        Args:
            completed_tables: List of completed table data dicts
            genie_yaml: Optional Genie space YAML
            skip_genie: Whether Genie YAML should be skipped
            tags: Optional list of tags

        Returns:
            Number of YAMLs saved (0 if unavailable)
        """
        if not self.is_available():
            logger.warning("Cannot save to library: Lakebase unavailable")
            return 0

        count = 0
        count += self._save_table_yamls(completed_tables, tags)

        if not skip_genie and genie_yaml and completed_tables:
            count += self._save_genie_yaml(genie_yaml, completed_tables, tags)

        return count

    def _save_table_yamls(self, completed_tables: List[Dict], tags: Optional[List[str]] = None) -> int:
        """
        Save table comment YAMLs to library (internal method).

        Args:
            completed_tables: List of completed table dicts with tier1_yaml
            tags: Optional list of tags

        Returns:
            Number of table YAMLs saved
        """
        count = 0

        for table_data in completed_tables:
            try:
                if not table_data.get('tier1_yaml'):
                    logger.warning(f"Skipping table without tier1_yaml: {table_data.get('table')}")
                    continue

                yaml_id = self.persistence.save_to_library(
                    catalog=table_data['catalog'],
                    schema=table_data['schema'],
                    table=table_data['table'],
                    yaml_content=table_data['tier1_yaml'],
                    yaml_type='table_comment',
                    metadata=table_data.get('metadata'),
                    tags=tags
                )
                if yaml_id:
                    count += 1
                    logger.info(f"Saved table YAML to library: {table_data['catalog']}.{table_data['schema']}.{table_data['table']}")
            except Exception as e:
                logger.error(f"Failed to save {table_data.get('table')} to library: {e}")

        return count

    def _save_genie_yaml(self, genie_yaml: str, completed_tables: List[Dict], tags: Optional[List[str]] = None) -> int:
        """
        Save Genie space YAML to library (internal method).

        Args:
            genie_yaml: Genie space YAML content
            completed_tables: List of tables for context
            tags: Optional list of tags

        Returns:
            1 if saved, 0 otherwise
        """
        try:
            # Use first table's catalog/schema for Genie YAML
            first_table = completed_tables[0]

            yaml_id = self.persistence.save_to_library(
                catalog=first_table['catalog'],
                schema=first_table['schema'],
                table='genie_space',
                yaml_content=genie_yaml,
                yaml_type='genie_space',
                metadata={'table_count': len(completed_tables)},
                tags=tags
            )
            if yaml_id:
                logger.info(f"Saved Genie YAML to library for {len(completed_tables)} tables")
                return 1
        except Exception as e:
            logger.error(f"Failed to save Genie YAML to library: {e}")

        return 0

    @_with_availability_check(default_return=[])
    def get_yamls(
        self,
        yaml_type: Optional[str] = None,
        catalog: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get YAMLs from library with optional filters.

        Returns empty list if unavailable.
        """
        return self.persistence.get_from_library(
            yaml_type=yaml_type,
            catalog=catalog,
            limit=limit
        )

    @_with_availability_check(default_return=[])
    def search_yamls(self, query: str, limit: int = 50) -> List[Dict]:
        """
        Search library by text query.

        Returns empty list if unavailable.
        """
        return self.persistence.search_library(query, limit=limit)

    @_with_availability_check(default_return=False)
    def delete_yaml(self, yaml_id: int) -> bool:
        """
        Delete YAML from library.

        Returns False if unavailable.
        """
        return self.persistence.delete_from_library(yaml_id)

    @_with_availability_check(default_return=False)
    def update_yaml(self, yaml_id: int, yaml_content: str) -> bool:
        """
        Update YAML content in library.

        Args:
            yaml_id: Library entry ID
            yaml_content: New YAML content

        Returns:
            True if update successful, False otherwise
        """
        return self.persistence.update_library_entry(yaml_id, yaml_content)


def get_library_service(user_email: str) -> LibraryService:
    """
    Get cached LibraryService instance, gracefully handling Lakebase unavailability.

    Uses session-state caching to avoid recreating the service on every call.
    Returns a LibraryService that will return empty results when Lakebase
    is unavailable, allowing the app to run with reduced functionality.

    Args:
        user_email: Current user's email

    Returns:
        Cached LibraryService instance (may be unavailable)
    """
    import streamlit as st
    from state.db import get_persistence_service

    # Cache the service instance per session
    if '_library_service' not in st.session_state:
        persistence = get_persistence_service(user_email)
        st.session_state._library_service = LibraryService(persistence)

    return st.session_state._library_service
