"""
Streamlit session_state backend for state storage.
"""
from typing import Any, List
import streamlit as st
from .base import StateBackend


class SessionStateBackend(StateBackend):
    """Streamlit session_state backend."""
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key."""
        return st.session_state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value by key."""
        st.session_state[key] = value
    
    def delete(self, key: str) -> None:
        """Delete a key."""
        if key in st.session_state:
            del st.session_state[key]
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return key in st.session_state
    
    def keys_with_prefix(self, prefix: str) -> List[str]:
        """Get all keys with given prefix."""
        return [k for k in st.session_state.keys() if k.startswith(prefix)]
    
    def clear_prefix(self, prefix: str) -> int:
        """Delete all keys with prefix, return count deleted."""
        keys = self.keys_with_prefix(prefix)
        for k in keys:
            del st.session_state[k]
        return len(keys)
