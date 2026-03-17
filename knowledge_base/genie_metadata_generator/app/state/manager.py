"""
Centralized state management for Genify.
"""
from typing import Optional, List, Dict
from .backends.base import StateBackend
from .context import SessionContext
from .models import TableIdentifier
import logging

logger = logging.getLogger(__name__)


class StateManager:
    """
    Centralized state management with clean API.
    
    All state keys are namespaced by session_key (user_email + start_time)
    to support multi-user environments and future database persistence.
    """
    
    # Key prefixes for organization (will be combined with session_key)
    PREFIX_PROFILE = "profile_"
    PREFIX_PENDING_DELETE = "pending_delete_"
    
    # Standard key names (will be prefixed with session namespace)
    KEY_WORKFLOW = "workflow_step"
    KEY_TABLE_QUEUE = "table_queue"
    KEY_COMPLETED_TABLES = "completed_tables"
    KEY_CURRENT_INDEX = "current_table_index"
    KEY_TABLE_INTERVIEW = "table_section_interview"
    KEY_GENIE_INTERVIEW = "genie_section_interview"
    KEY_TIER2_YAML = "tier2_yaml"
    KEY_HISTORY = "history"
    KEY_EDIT_INDEX = "edit_table_index"
    KEY_SKIP_GENIE = "skip_genie"
    
    def __init__(self, backend: StateBackend, context: SessionContext):
        self.backend = backend
        self.context = context
        logger.info(f"StateManager initialized for user: {context.display_name}, session: {context.session_key}")
    
    def _key(self, name: str) -> str:
        """
        Generate namespaced key for storage.
        
        Format: {session_key}:{key_name}
        This ensures user sessions are isolated and enables
        database queries by session_key.
        """
        return f"{self.context.session_key}:{name}"
    
    @property
    def user_email(self) -> str:
        """Get current user's email."""
        return self.context.user_email
    
    @property
    def session_key(self) -> str:
        """Get current session's unique key."""
        return self.context.session_key
    
    @property
    def session_info(self) -> dict:
        """Get session metadata for display/logging."""
        return self.context.to_dict()
    
    # === Workflow ===
    def get_workflow_step(self) -> str:
        """Get current workflow step."""
        return self.backend.get(self._key(self.KEY_WORKFLOW), "browse")
    
    def set_workflow_step(self, step: str) -> None:
        """Set current workflow step."""
        self.backend.set(self._key(self.KEY_WORKFLOW), step)
    
    # === Profiles ===
    def _profile_key(self, table_id: TableIdentifier) -> str:
        """Generate namespaced profile key."""
        return self._key(f"{self.PREFIX_PROFILE}{table_id.key}")
    
    def get_profile(self, table_id: TableIdentifier) -> Optional[Dict]:
        """Get profile data for a table."""
        key = self._profile_key(table_id)
        return self.backend.get(key)
    
    def set_profile(self, table_id: TableIdentifier, profile_data: Dict, summary: str) -> None:
        """Store profile for a table."""
        key = self._profile_key(table_id)
        self.backend.set(key, {
            'profile': profile_data,
            'summary': summary
        })
    
    def has_profile(self, table_id: TableIdentifier) -> bool:
        """Check if table has a profile."""
        key = self._profile_key(table_id)
        data = self.backend.get(key)
        return data is not None
    
    def get_profile_summary(self, table_id: TableIdentifier) -> Optional[str]:
        """Get just the profile summary for a table."""
        data = self.get_profile(table_id)
        return data.get('summary') if data else None
    
    def clear_profile(self, table_id: TableIdentifier) -> None:
        """Remove profile for a table."""
        self.backend.delete(self._profile_key(table_id))
    
    # === Table Queue ===
    def get_table_queue(self) -> List[Dict]:
        """Get all tables in the queue."""
        return self.backend.get(self._key(self.KEY_TABLE_QUEUE), [])
    
    def add_to_queue(self, table_data: Dict) -> bool:
        """Add table to queue. Returns False if already in queue."""
        queue = self.get_table_queue()
        table_key = f"{table_data['catalog']}_{table_data['schema']}_{table_data['table']}"
        
        # Check for duplicates
        for t in queue:
            existing_key = f"{t['catalog']}_{t['schema']}_{t['table']}"
            if existing_key == table_key:
                return False
        
        queue.append(table_data)
        self.backend.set(self._key(self.KEY_TABLE_QUEUE), queue)
        return True
    
    def set_table_queue(self, queue: List[Dict]) -> None:
        """Replace entire queue."""
        self.backend.set(self._key(self.KEY_TABLE_QUEUE), queue)
    
    def clear_queue(self) -> None:
        """Clear the table queue."""
        self.backend.set(self._key(self.KEY_TABLE_QUEUE), [])
    
    def get_current_table_index(self) -> int:
        """Get current table index in queue."""
        return self.backend.get(self._key(self.KEY_CURRENT_INDEX), 0)
    
    def set_current_table_index(self, index: int) -> None:
        """Set current table index."""
        self.backend.set(self._key(self.KEY_CURRENT_INDEX), index)
    
    # === Completed Tables ===
    def get_completed_tables(self) -> List[Dict]:
        """Get all completed tables."""
        return self.backend.get(self._key(self.KEY_COMPLETED_TABLES), [])
    
    def add_completed_table(self, table_data: Dict) -> int:
        """Add or update completed table. Returns index."""
        tables = self.get_completed_tables()
        table_key = f"{table_data['catalog']}_{table_data['schema']}_{table_data['table']}"
        
        # Check if already exists
        existing_idx = None
        for idx, t in enumerate(tables):
            existing_key = f"{t['catalog']}_{t['schema']}_{t['table']}"
            if existing_key == table_key:
                existing_idx = idx
                break
        
        if existing_idx is not None:
            tables[existing_idx] = table_data
            result_idx = existing_idx
        else:
            tables.append(table_data)
            result_idx = len(tables) - 1
        
        self.backend.set(self._key(self.KEY_COMPLETED_TABLES), tables)
        return result_idx
    
    def remove_completed_table(self, index: int) -> bool:
        """Remove completed table by index. Returns True if removed."""
        tables = self.get_completed_tables()
        if 0 <= index < len(tables):
            tables.pop(index)
            self.backend.set(self._key(self.KEY_COMPLETED_TABLES), tables)
            return True
        return False
    
    def get_completed_table(self, index: int) -> Optional[Dict]:
        """Get a specific completed table by index."""
        tables = self.get_completed_tables()
        if 0 <= index < len(tables):
            return tables[index]
        return None
    
    def update_completed_table(self, index: int, table_data: Dict) -> bool:
        """Update a completed table at index. Returns True if updated."""
        tables = self.get_completed_tables()
        if 0 <= index < len(tables):
            tables[index] = table_data
            self.backend.set(self._key(self.KEY_COMPLETED_TABLES), tables)
            return True
        return False
    
    # === Pending Deletes (for confirmation UI) ===
    def _pending_delete_key(self, index: int) -> str:
        """Generate key for pending delete flag."""
        return self._key(f"{self.PREFIX_PENDING_DELETE}{index}")
    
    def is_pending_delete(self, index: int) -> bool:
        """Check if table at index is pending deletion."""
        return self.backend.get(self._pending_delete_key(index), False)
    
    def set_pending_delete(self, index: int, pending: bool = True) -> None:
        """Set pending delete flag for table."""
        self.backend.set(self._pending_delete_key(index), pending)
    
    def clear_pending_delete(self, index: int) -> None:
        """Clear pending delete flag."""
        self.backend.delete(self._pending_delete_key(index))
    
    def clear_all_pending_deletes(self) -> None:
        """Clear all pending delete flags."""
        prefix = self._key(self.PREFIX_PENDING_DELETE)
        self.backend.clear_prefix(prefix)
    
    # === Interviews ===
    # Note: Interview objects are serialized to/from dicts for database persistence.
    # When using SessionStateBackend, the object is stored directly for backward compatibility.
    # When using LakebaseBackend, the object is serialized via to_dict()/from_dict().
    
    def _create_llm_client(self):
        """Create a fresh LLM client for interview deserialization."""
        from llm.client import get_main_llm_client
        return get_main_llm_client()
    
    def _is_serialized_interview(self, data) -> bool:
        """Check if data is a serialized interview dict vs live object."""
        return isinstance(data, dict) and 'config_path' in data and 'current_section_idx' in data
    
    def _get_interview(self, key: str, interview_type: str):
        """
        Generic interview getter with deserialization.
        
        Args:
            key: State key for the interview
            interview_type: 'table' or 'genie' for logging
        
        Returns:
            Interview object or None
        """
        data = self.backend.get(self._key(key))
        if data is None:
            return None
        
        # If it's already an interview object (SessionStateBackend), return as-is
        if not self._is_serialized_interview(data):
            return data
        
        # Deserialize from dict (LakebaseBackend or restored session)
        from llm.section_interview import SectionBasedInterview
        from state.services import get_context_summarizer_service
        
        # Create fresh LLM client
        llm = self._create_llm_client()
        
        # Get context summarizer service with dedicated Gemini Flash endpoint
        from llm.client import get_summarizer_llm_client
        llm_for_summarizer = get_summarizer_llm_client()
        context_summarizer = get_context_summarizer_service(llm_for_summarizer)
        
        # Deserialize with both dependencies
        interview = SectionBasedInterview.from_dict(data, llm, context_summarizer)
        logger.info(f"Deserialized {interview_type} interview at section {interview.current_section_idx + 1}")
        return interview
    
    def _set_interview(self, key: str, interview, interview_type: str) -> None:
        """
        Generic interview setter with serialization.
        
        Args:
            key: State key for the interview
            interview: Interview object or None
            interview_type: 'table' or 'genie' for logging
        """
        if interview is None:
            self.backend.delete(self._key(key))
            return
        
        # Serialize for storage (works with both backends)
        if hasattr(interview, 'to_dict'):
            data = interview.to_dict()
            self.backend.set(self._key(key), data)
            logger.debug(f"Serialized {interview_type} interview at section {interview.current_section_idx + 1}")
        else:
            # Fallback for backward compatibility
            self.backend.set(self._key(key), interview)
    
    def get_table_interview(self):
        """
        Get current table interview object.
        
        If the backend returns serialized dict data (from database),
        deserialize it back into a SectionBasedInterview instance.
        """
        return self._get_interview(self.KEY_TABLE_INTERVIEW, 'table')
    
    def set_table_interview(self, interview) -> None:
        """
        Store table interview object.
        
        The interview is serialized to dict for database persistence.
        This ensures the interview state can be restored later.
        """
        self._set_interview(self.KEY_TABLE_INTERVIEW, interview, 'table')
    
    def clear_table_interview(self) -> None:
        """Clear table interview."""
        self.backend.delete(self._key(self.KEY_TABLE_INTERVIEW))
    
    def get_genie_interview(self):
        """
        Get Genie interview object.
        
        If the backend returns serialized dict data (from database),
        deserialize it back into a SectionBasedInterview instance.
        """
        return self._get_interview(self.KEY_GENIE_INTERVIEW, 'genie')
    
    def set_genie_interview(self, interview) -> None:
        """
        Store Genie interview object.
        
        The interview is serialized to dict for database persistence.
        """
        self._set_interview(self.KEY_GENIE_INTERVIEW, interview, 'genie')
    
    def clear_genie_interview(self) -> None:
        """Clear Genie interview."""
        self.backend.delete(self._key(self.KEY_GENIE_INTERVIEW))
    
    # === Tier 2 YAML ===
    def get_tier2_yaml(self) -> Optional[str]:
        """Get Genie space YAML."""
        return self.backend.get(self._key(self.KEY_TIER2_YAML))
    
    def set_tier2_yaml(self, yaml_content: str) -> None:
        """Store Genie space YAML."""
        self.backend.set(self._key(self.KEY_TIER2_YAML), yaml_content)
    
    # === Edit State ===
    def get_edit_table_index(self) -> Optional[int]:
        """Get index of table being edited."""
        return self.backend.get(self._key(self.KEY_EDIT_INDEX))
    
    def set_edit_table_index(self, index: int) -> None:
        """Set table index for editing."""
        self.backend.set(self._key(self.KEY_EDIT_INDEX), index)
    
    def clear_edit_table_index(self) -> None:
        """Clear edit index."""
        self.backend.delete(self._key(self.KEY_EDIT_INDEX))
    
    # === Skip Genie Flag ===
    def get_skip_genie(self) -> bool:
        """Check if Genie interview should be skipped."""
        return self.backend.get(self._key(self.KEY_SKIP_GENIE), False)
    
    def set_skip_genie(self, skip: bool) -> None:
        """Set skip Genie flag."""
        self.backend.set(self._key(self.KEY_SKIP_GENIE), skip)
    
    # === History ===
    def get_history(self) -> List[Dict]:
        """Get session history."""
        return self.backend.get(self._key(self.KEY_HISTORY), [])
    
    def add_to_history(self, item: Dict) -> None:
        """Add item to history."""
        history = self.get_history()
        history.append(item)
        self.backend.set(self._key(self.KEY_HISTORY), history)
    
    def clear_history(self) -> None:
        """Clear session history."""
        self.backend.set(self._key(self.KEY_HISTORY), [])
    
    # === Connection Management ===
    # CRITICAL: Connections MUST be stored directly in session_state
    # Connection objects cannot be serialized to JSON for database storage
    def get_connection(self):
        """Get database connection (stored in session_state, not backend)."""
        import streamlit as st
        return st.session_state.get("_sql_connection")
    
    def set_connection(self, connection) -> None:
        """Store database connection (in session_state, not backend)."""
        import streamlit as st
        st.session_state["_sql_connection"] = connection
    
    # === Session Management ===
    def reset_session(self) -> None:
        """Clear all state for a fresh start (keeps connection)."""
        logger.info(f"Resetting session for {self.context.display_name}")
        
        keys_to_clear = [
            self.KEY_TABLE_QUEUE, self.KEY_COMPLETED_TABLES,
            self.KEY_CURRENT_INDEX, self.KEY_TABLE_INTERVIEW,
            self.KEY_GENIE_INTERVIEW, self.KEY_TIER2_YAML,
            self.KEY_EDIT_INDEX, self.KEY_SKIP_GENIE, self.KEY_HISTORY
        ]
        for key in keys_to_clear:
            self.backend.delete(self._key(key))
        
        # Clear dynamic keys with session prefix
        session_prefix = f"{self.context.session_key}:"
        self.backend.clear_prefix(session_prefix + self.PREFIX_PROFILE)
        self.backend.clear_prefix(session_prefix + self.PREFIX_PENDING_DELETE)
        
        # Reset to browse
        self.set_workflow_step("browse")
    
    def get_session_summary(self) -> Dict:
        """Get summary of current session state for debugging/display."""
        return {
            # User identity (from Databricks Apps headers)
            "user": self.context.display_name,
            "user_email": self.context.user_email,
            "user_id": self.context.user_id,
            "username": self.context.username,
            "client_ip": self.context.client_ip,
            "is_authenticated": self.context.is_authenticated,
            # Session info
            "session_key": self.context.session_key,
            "session_start": self.context.session_start.isoformat(),
            # Workflow state
            "workflow_step": self.get_workflow_step(),
            "tables_in_queue": len(self.get_table_queue()),
            "tables_completed": len(self.get_completed_tables()),
            "has_tier2_yaml": self.get_tier2_yaml() is not None
        }
    
    # === Save/Restore Progress ===
    
    def save_progress(self, session_name: Optional[str] = None, add_to_library: bool = False, target_session_key: Optional[str] = None) -> Optional[int]:
        """
        Save current state to Lakebase - ALL state including interviews.
        
        This is an EXPLICIT save - nothing is persisted until user clicks "Save Progress".
        
        What gets saved:
        1. Completed tables → genify.saved_tables (with full YAMLs)
        2. Current interview state → genify.session_snapshots
           - Serializes active table_interview if exists
           - Serializes active genie_interview if exists
           - Saves table queue
           - Saves current index
        3. Session metadata → genify.sessions
        4. Always → genify.yaml_library (both table and Genie YAMLs when add_to_library=True)
        
        Args:
            session_name: Optional user-provided name for this session
            add_to_library: If True, save completed YAMLs to library (UI always passes True)
            target_session_key: Optional session key to overwrite (for updating existing sessions)
        
        Returns:
            session_id from database, or None if Lakebase not available
        """
        try:
            from config import config
            from state.db import get_persistence_service
            
            if not config.lakebase_enabled:
                logger.warning("Cannot save progress: Lakebase not enabled")
                return None
            
            persistence = get_persistence_service(self.user_email)
            if not persistence:
                logger.warning("Cannot save progress: Lakebase connection not available")
                return None
            
            # Get library service if saving to library
            library_service = None
            if add_to_library:
                from state.services import get_library_service
                library_service = get_library_service(self.user_email)
            
            # Use target_session_key if provided (for overwrites), otherwise use current session_key
            save_key = target_session_key if target_session_key else self.session_key
            
            session_id = persistence.save_session(
                session_key=save_key,
                state_manager=self,
                session_name=session_name,
                add_to_library=add_to_library,
                library_service=library_service
            )
            
            action = "updated" if target_session_key else "saved"
            logger.info(f"✓ Progress {action}: session_id={session_id}, name={session_name}, key={save_key}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error saving progress: {e}", exc_info=True)
            return None
    
    def restore_from_session(self, session_key: str) -> bool:
        """
        Load saved session into current state - FULL restore.
        
        Restores:
        1. Completed tables (with YAMLs)
        2. Table queue
        3. Current table index
        4. Deserializes table_interview if was mid-interview
        5. Deserializes genie_interview if was mid-interview
        6. Workflow step
        7. Genie YAML if complete
        
        Args:
            session_key: Session key to restore from database
        
        Returns:
            True if successful, False otherwise
        """
        try:
            from config import config
            from state.db import get_persistence_service
            from llm.section_interview import SectionBasedInterview
            
            if not config.lakebase_enabled:
                logger.warning("Cannot restore session: Lakebase not enabled")
                return False
            
            persistence = get_persistence_service(self.user_email)
            if not persistence:
                logger.warning("Cannot restore session: Lakebase connection not available")
                return False
            
            data = persistence.restore_session(session_key)
            
            if not data:
                logger.warning(f"Session not found: {session_key}")
                return False
            
            # Clear current state first
            self.clear_queue()
            self.backend.set(self._key(self.KEY_COMPLETED_TABLES), [])
            self.clear_table_interview()
            self.clear_genie_interview()
            
            # Restore completed tables
            for table in data['completed_tables']:
                self.add_completed_table(table)
            
            # Restore queue and index
            self.set_table_queue(data['table_queue'])
            self.set_current_table_index(data['current_table_index'])
            
            # Restore workflow step
            self.set_workflow_step(data['workflow_step'])
            
            # Deserialize table interview if exists
            from state.services import get_context_summarizer_service
            from config import config
            
            llm = self._create_llm_client()
            
            # Get context summarizer service with dedicated Gemini Flash endpoint
            from llm.client import get_summarizer_llm_client
            llm_for_summarizer = get_summarizer_llm_client()
            context_summarizer = get_context_summarizer_service(llm_for_summarizer)
            
            if data['table_interview']:
                interview = SectionBasedInterview.from_dict(
                    data['table_interview'],
                    llm,
                    context_summarizer
                )
                self.set_table_interview(interview)
                logger.info(f"Restored table interview at section {interview.current_section_idx + 1}")
            
            # Deserialize genie interview if exists
            if data['genie_interview']:
                interview = SectionBasedInterview.from_dict(
                    data['genie_interview'],
                    llm,
                    context_summarizer
                )
                self.set_genie_interview(interview)
                logger.info(f"Restored genie interview at section {interview.current_section_idx + 1}")
            
            # Restore Genie YAML if exists
            if data['genie_yaml']:
                self.set_tier2_yaml(data['genie_yaml'])
            
            logger.info(f"✓ Session restored successfully: {len(data['completed_tables'])} tables, "
                       f"workflow={data['workflow_step']}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring session: {e}", exc_info=True)
            return False
    
    def get_unsaved_count(self) -> int:
        """
        Count items that haven't been saved.
        For UI indicator (unsaved changes badge).
        
        Returns:
            Number of unsaved items (completed tables + in-progress interviews)
        """
        count = 0
        
        # Count completed tables
        count += len(self.get_completed_tables())
        
        # Count in-progress interviews
        if self.get_table_interview():
            count += 1
        
        if self.get_genie_interview():
            count += 1
        
        # Count queued tables (if any work has been done)
        queue = self.get_table_queue()
        if queue:
            count += len(queue)
        
        return count
    
    def list_sessions(self, limit: int = 10) -> list:
        """
        List user's saved sessions.
        
        Args:
            limit: Maximum number of sessions to return
        
        Returns:
            List of session dicts, or empty list if unavailable
        """
        try:
            from config import config
            from state.db import get_persistence_service
            
            if not config.lakebase_enabled:
                return []
            
            persistence = get_persistence_service(self.user_email)
            if not persistence:
                return []
            
            return persistence.list_user_sessions(limit=limit)
            
        except Exception as e:
            logger.error(f"Error listing sessions: {e}", exc_info=True)
            return []
    
    def rename_session(self, session_key: str, new_name: str) -> bool:
        """Rename a saved session."""
        try:
            from config import config
            from state.db import get_persistence_service
            
            if not config.lakebase_enabled:
                logger.warning("Cannot rename session: Lakebase not enabled")
                return False
            
            persistence = get_persistence_service(self.user_email)
            if not persistence:
                logger.warning("Cannot rename session: Lakebase connection not available")
                return False
            
            return persistence.rename_session(session_key, new_name)
            
        except Exception as e:
            logger.error(f"Error renaming session: {e}", exc_info=True)
            return False
    
    def delete_session(self, session_key: str) -> bool:
        """Delete a saved session."""
        try:
            from config import config
            from state.db import get_persistence_service
            
            if not config.lakebase_enabled:
                logger.warning("Cannot delete session: Lakebase not enabled")
                return False
            
            persistence = get_persistence_service(self.user_email)
            if not persistence:
                logger.warning("Cannot delete session: Lakebase connection not available")
                return False
            
            return persistence.delete_session(session_key)
            
        except Exception as e:
            logger.error(f"Error deleting session: {e}", exc_info=True)
            return False