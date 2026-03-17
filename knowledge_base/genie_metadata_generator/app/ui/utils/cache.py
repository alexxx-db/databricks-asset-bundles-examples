"""
Caching utilities for Streamlit UI components.

Provides session-state based caching with TTL and invalidation support.
"""

import streamlit as st
from typing import Any, Callable, Optional, List
import time


def cached_state(
    key: str,
    compute_fn: Callable,
    ttl_seconds: Optional[int] = None,
    invalidate_on: Optional[List[str]] = None
) -> Any:
    """
    Cache result in session_state with optional TTL and invalidation.
    
    Args:
        key: Unique cache key
        compute_fn: Function to compute value if not cached
        ttl_seconds: Time-to-live in seconds (None = no expiration)
        invalidate_on: List of session_state keys to watch for changes
        
    Returns:
        Cached or freshly computed value
        
    Example:
        >>> sessions = cached_state(
        ...     "history_sessions",
        ...     lambda: state.list_sessions(limit=10),
        ...     ttl_seconds=30
        ... )
    """
    cache_key = f"_cache_{key}"
    timestamp_key = f"_cache_{key}_ts"
    hash_key = f"_cache_{key}_hash"
    
    # Check TTL expiration
    if ttl_seconds and timestamp_key in st.session_state:
        if time.time() - st.session_state[timestamp_key] > ttl_seconds:
            # Expired - clear cache
            if cache_key in st.session_state:
                del st.session_state[cache_key]
                if timestamp_key in st.session_state:
                    del st.session_state[timestamp_key]
    
    # Check invalidation keys
    if invalidate_on:
        current_hash = hash(tuple(st.session_state.get(k) for k in invalidate_on))
        if hash_key in st.session_state and st.session_state[hash_key] != current_hash:
            # Invalidate - clear cache
            if cache_key in st.session_state:
                del st.session_state[cache_key]
                if timestamp_key in st.session_state:
                    del st.session_state[timestamp_key]
        st.session_state[hash_key] = current_hash
    
    # Return cached or compute
    if cache_key not in st.session_state:
        st.session_state[cache_key] = compute_fn()
        st.session_state[timestamp_key] = time.time()
    
    return st.session_state[cache_key]


def invalidate_cache(key: str):
    """
    Manually invalidate a cache entry.
    
    Args:
        key: Cache key to invalidate
    """
    cache_key = f"_cache_{key}"
    timestamp_key = f"_cache_{key}_ts"
    hash_key = f"_cache_{key}_hash"
    
    for k in [cache_key, timestamp_key, hash_key]:
        if k in st.session_state:
            del st.session_state[k]
