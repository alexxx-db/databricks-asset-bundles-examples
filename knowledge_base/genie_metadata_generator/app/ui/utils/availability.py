"""
Utilities for checking service availability and showing appropriate UI feedback.
"""
import streamlit as st
from config import config


def check_lakebase_available(warning_message: str = "This feature requires Lakebase to be enabled") -> bool:
    """
    Check if Lakebase is available and show warning if not.
    
    Args:
        warning_message: Message to display if Lakebase unavailable
    
    Returns:
        True if available, False otherwise
    """
    if not config.lakebase_enabled:
        st.warning(warning_message, icon=":material/warning:")
        return False
    return True


def check_library_service_available(library_service, warning_message: str = "Lakebase connection not available") -> bool:
    """
    Check if library service is available and show warning if not.
    
    Args:
        library_service: LibraryService instance
        warning_message: Message to display if unavailable
    
    Returns:
        True if available, False otherwise
    """
    if not library_service.is_available():
        st.warning(warning_message, icon=":material/warning:")
        return False
    return True
