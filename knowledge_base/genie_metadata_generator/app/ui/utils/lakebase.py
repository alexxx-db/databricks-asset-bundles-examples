"""
Lakebase connection utilities for UI components.

Provides centralized Lakebase connection checking with caching.
"""

import streamlit as st
from state.db import get_lakebase_connection_safe


@st.cache_data(ttl=10, show_spinner=False)
def is_lakebase_connected() -> bool:
    """
    Check if Lakebase is connected (cached for 10 seconds).

    Returns:
        True if Lakebase connection is available, False otherwise
    """
    try:
        connection = get_lakebase_connection_safe()
        return connection is not None
    except Exception:
        return False


def check_lakebase_available() -> bool:
    """
    Check and show UI feedback if Lakebase unavailable.

    Returns:
        True if Lakebase is available, False otherwise

    Example:
        >>> if not check_lakebase_available():
        ...     return  # Exit early if Lakebase not available
    """
    if not is_lakebase_connected():
        st.warning("⚠️ Lakebase not available - feature requires database connection")
        return False
    return True
