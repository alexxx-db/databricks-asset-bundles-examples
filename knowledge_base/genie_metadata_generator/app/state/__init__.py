"""
State management module for Genify.

Usage:
    from state import get_state_manager
    
    state = get_state_manager()
    state.set_workflow_step("browse")
    tables = state.get_completed_tables()

Backends:
    - SessionStateBackend: In-memory (Streamlit session_state) - default
    - LakebaseBackend: PostgreSQL (persistent) - enabled via config
"""

from .manager import StateManager
from .backends.session import SessionStateBackend
from .context import SessionContext, get_session_context, get_user_email
from .models import TableIdentifier

import streamlit as st
import logging

logger = logging.getLogger(__name__)


def _create_backend(context: SessionContext):
    """
    Create the appropriate state backend based on configuration.
    
    Priority:
    1. If Lakebase is enabled and configured, use LakebaseBackend
    2. Otherwise, use SessionStateBackend (in-memory)
    
    Args:
        context: Session context with user info
        
    Returns:
        StateBackend instance
    """
    from config import config
    
    if config.lakebase_enabled:
        try:
            from .backends.lakebase import LakebaseBackend
            from .db import get_lakebase_connection
            
            connection = get_lakebase_connection()
            backend = LakebaseBackend(
                connection=connection,
                session_key=context.session_key,
                user_email=context.user_email,
                schema=config.lakebase_schema,
                table=config.lakebase_table
            )
            logger.info("Using LakebaseBackend for persistent state")
            return backend
            
        except ImportError as e:
            logger.warning(f"Lakebase dependencies not available: {e}. Falling back to SessionStateBackend.")
        except Exception as e:
            logger.warning(f"Failed to initialize LakebaseBackend: {e}. Falling back to SessionStateBackend.")
    
    # Default: in-memory backend
    logger.debug("Using SessionStateBackend (in-memory)")
    return SessionStateBackend()


def get_state_manager() -> StateManager:
    """
    Get or create StateManager for current user session.
    
    The StateManager is tied to:
    1. User email (from X-Forwarded-Email header)
    2. Session start time
    
    This allows:
    - Multi-user isolation
    - Session tracking
    - Database persistence when Lakebase is enabled
    - Resume functionality for returning users
    """
    # Use session_state to cache the manager per Streamlit session
    if "_state_manager" not in st.session_state:
        context = get_session_context()
        backend = _create_backend(context)
        st.session_state._state_manager = StateManager(backend, context)
    
    return st.session_state._state_manager


# Convenience exports
__all__ = [
    "get_state_manager",
    "StateManager", 
    "SessionContext",
    "get_session_context",
    "get_user_email",
    "TableIdentifier"
]
