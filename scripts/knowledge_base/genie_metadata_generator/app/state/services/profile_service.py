"""
Profile service for table profiling operations.

Single source of truth for profile generation and caching.
"""
import logging
from typing import Optional, Dict, Tuple
from state import StateManager, TableIdentifier
from data.profiler import get_table_profile
from data.profile_formatter import format_profile_for_llm

logger = logging.getLogger(__name__)


class ProfileService:
    """Service for table profiling with caching."""

    def __init__(self, state_manager: StateManager):
        """
        Initialize profile service.

        Args:
            state_manager: StateManager instance for caching
        """
        self.state = state_manager

    def has_profile(self, catalog: str, schema: str, table: str, table_data: Optional[Dict] = None) -> bool:
        """
        Check if profile exists in cache or table_data.

        Args:
            catalog: Catalog name
            schema: Schema name
            table: Table name
            table_data: Optional table_data dict to check for profile_summary

        Returns:
            True if profile exists
        """
        table_id = TableIdentifier(catalog=catalog, schema=schema, table=table)

        # Check StateManager cache
        if self.state.has_profile(table_id):
            return True

        # Check table_data metadata using utility function
        if table_data:
            from utils.data_conversion import get_profile_summary
            if get_profile_summary(table_data):
                return True

        return False

    def get_profile(self, catalog: str, schema: str, table: str, table_data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Get profile from cache or table_data.

        Args:
            catalog: Catalog name
            schema: Schema name
            table: Table name
            table_data: Optional table_data dict to check

        Returns:
            Profile dict or None if not found
        """
        table_id = TableIdentifier(catalog=catalog, schema=schema, table=table)

        # Check StateManager cache first
        profile_data = self.state.get_profile(table_id)
        if profile_data:
            return profile_data

        # Check table_data metadata
        if table_data and 'profile_summary' in table_data.get('metadata', {}):
            return {'summary': table_data['metadata']['profile_summary']}

        return None

    def generate_profile(
        self,
        connection,
        catalog: str,
        schema: str,
        table: str,
        columns: list,
        table_data: Optional[Dict] = None
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Generate profile for a table.

        Args:
            connection: Database connection
            catalog: Catalog name
            schema: Schema name
            table: Table name
            columns: List of column dicts
            table_data: Optional table_data to update

        Returns:
            (success: bool, profile_data: Optional[Dict], error: Optional[str])
        """
        table_id = TableIdentifier(catalog=catalog, schema=schema, table=table)

        try:
            # Generate profile
            profile = get_table_profile(connection, catalog, schema, table, columns)

            # Check for errors in profile
            if profile.get("table_stats", {}).get("errors"):
                logger.warning(f"Profile generated with errors: {profile['table_stats']['errors']}")

            # Format for LLM
            profile_summary = format_profile_for_llm(profile)

            # Store in cache
            self.state.set_profile(table_id, profile, profile_summary)

            # Update table_data if provided
            if table_data is not None:
                if 'metadata' not in table_data:
                    table_data['metadata'] = {}
                table_data['metadata']['profile_summary'] = profile_summary

            logger.info(f"Profile generated for {catalog}.{schema}.{table}")
            return (True, {'summary': profile_summary, 'profile': profile}, None)

        except Exception as e:
            error_msg = f"Failed to generate profile: {str(e)}"
            logger.error(f"{error_msg}", exc_info=True)
            return (False, None, error_msg)

    def clear_profile(self, catalog: str, schema: str, table: str):
        """Clear profile from cache."""
        table_id = TableIdentifier(catalog=catalog, schema=schema, table=table)
        self.state.clear_profile(table_id)
        logger.info(f"Profile cleared for {catalog}.{schema}.{table}")

    def generate_profiles_batch(
        self,
        connection,
        table_data_list: list
    ) -> dict:
        """
        Generate profiles for multiple tables (sequential, following LibraryService pattern).

        Each table is profiled independently. Failures don't stop processing.
        Results are automatically cached via generate_profile().

        Args:
            connection: Database connection
            table_data_list: List of dicts with catalog, schema, table, columns

        Returns:
            Dict mapping "catalog.schema.table" to (success, profile_data, error) tuples
        """
        results = {}

        for table_data in table_data_list:
            catalog = table_data['catalog']
            schema = table_data['schema']
            table = table_data['table']
            columns = table_data.get('columns', [])
            table_key = f"{catalog}.{schema}.{table}"

            try:
                # Use existing generate_profile method (auto-caches)
                success, profile_data, error = self.generate_profile(
                    connection, catalog, schema, table, columns
                )
                results[table_key] = (success, profile_data, error)

                if success:
                    logger.info(f"Batch: Profiled {table_key}")
                else:
                    logger.warning(f"Batch: Failed to profile {table_key}: {error}")

            except Exception as e:
                logger.error(f"Batch profiling error for {table_key}: {e}")
                results[table_key] = (False, None, str(e))

        success_count = sum(1 for s, _, _ in results.values() if s)
        logger.info(f"Batch profiling complete: {success_count}/{len(table_data_list)} successful")

        return results


def get_profile_service(state_manager: StateManager) -> ProfileService:
    """
    Get cached ProfileService instance.

    Uses session-state caching to avoid recreating the service on every call.

    Args:
        state_manager: StateManager instance

    Returns:
        Cached ProfileService instance
    """
    import streamlit as st

    # Cache the service instance per session
    if '_profile_service' not in st.session_state:
        st.session_state._profile_service = ProfileService(state_manager)

    return st.session_state._profile_service
