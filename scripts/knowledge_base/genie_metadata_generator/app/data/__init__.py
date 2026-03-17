"""Data layer - profiling and Unity Catalog access."""
from .profiler import get_table_profile, get_table_statistics
from .profile_formatter import format_profile_for_llm
from .information_schema import (
    list_catalogs,
    list_schemas,
    list_tables,
    get_table_columns,
    get_table_metadata,
    build_table_context
)

__all__ = [
    "get_table_profile",
    "get_table_statistics",
    "format_profile_for_llm",
    "list_catalogs",
    "list_schemas",
    "list_tables",
    "get_table_columns",
    "get_table_metadata",
    "build_table_context"
]
