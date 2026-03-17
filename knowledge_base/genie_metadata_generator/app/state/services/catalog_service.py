"""
Catalog service for Unity Catalog browsing with caching.

Handles catalog, schema, and table queries with TTL-based caching.

NOTE: This service uses Streamlit's @st.cache_data decorator for performance optimization.
While this creates a dependency on the UI framework, it's acceptable because:
1. Catalog browsing is inherently a UI operation
2. The caching is simple and transparent (TTL-based)
3. The service remains testable with mock connections
4. Benefits outweigh the coupling cost (5min cache significantly improves UX)

For a pure framework-agnostic approach, consider using functools.lru_cache with
a custom cache invalidation strategy, but this adds complexity for minimal benefit.
"""
import streamlit as st
from typing import List, Tuple, Optional, Dict
from data.information_schema import (
    list_catalogs,
    list_schemas,
    list_tables,
    build_table_context
)


class CatalogService:
    """Service for Unity Catalog browsing with caching."""
    
    def __init__(self, connection, connection_id: str, cache_ttl: int = 300):
        """
        Initialize catalog service.
        
        Args:
            connection: Database connection
            connection_id: Unique identifier for cache key
            cache_ttl: Cache time-to-live in seconds (default 5 minutes)
        """
        self.connection = connection
        self.connection_id = connection_id
        self.cache_ttl = cache_ttl
    
    @staticmethod
    @st.cache_data(ttl=300, show_spinner=False)
    def _cached_list_catalogs(_connection_id: str, _connection) -> List[Tuple]:
        """Get catalogs with caching."""
        return list_catalogs(_connection)
    
    @staticmethod
    @st.cache_data(ttl=300, show_spinner=False)
    def _cached_list_schemas(_connection_id: str, catalog: str, _connection) -> List[Tuple]:
        """Get schemas with caching."""
        return list_schemas(_connection, catalog)
    
    @staticmethod
    @st.cache_data(ttl=300, show_spinner=False)
    def _cached_list_tables(_connection_id: str, catalog: str, schema: str, _connection) -> List[Tuple]:
        """Get tables with caching."""
        return list_tables(_connection, catalog, schema)
    
    def get_catalogs(self) -> List[Tuple]:
        """Get list of catalogs."""
        return self._cached_list_catalogs(self.connection_id, self.connection)
    
    def get_schemas(self, catalog: str) -> List[Tuple]:
        """Get list of schemas in catalog."""
        return self._cached_list_schemas(self.connection_id, catalog, self.connection)
    
    def get_tables(self, catalog: str, schema: str) -> List[Tuple]:
        """Get list of tables in schema."""
        return self._cached_list_tables(self.connection_id, catalog, schema, self.connection)
    
    @st.cache_data(ttl=300, show_spinner=False)
    def get_table_context(_self, catalog: str, schema: str, table: str) -> Optional[Dict]:
        """
        Build comprehensive table context (cached for 5 minutes).
        
        Args:
            catalog: Catalog name
            schema: Schema name
            table: Table name
        
        Returns:
            Table context dict or None
            
        Note:
            Self is prefixed with _ to skip hashing in cache.
        """
        context = build_table_context(_self.connection, catalog, schema, table)
        
        # Note: Statistics removed - use ProfileService.generate_profile() for profiling
        # CatalogService focuses solely on catalog browsing
        
        return context


def get_catalog_service(connection, connection_id: str) -> CatalogService:
    """
    Get cached CatalogService instance.
    
    Uses session-state caching per connection_id to avoid recreating the service.
    
    Args:
        connection: Database connection
        connection_id: Unique identifier for caching
    
    Returns:
        Cached CatalogService instance for this connection
    """
    import streamlit as st
    
    # Cache per connection_id since service is connection-specific
    cache_key = f'_catalog_service_{connection_id}'
    if cache_key not in st.session_state:
        st.session_state[cache_key] = CatalogService(connection, connection_id)
    
    return st.session_state[cache_key]
