"""
Collapsible history panel for the left sidebar.
Shows saved sessions with Material Design cards and restore dialogs.
Includes Save Progress functionality for session management.
"""

import logging
import streamlit as st
from state import get_state_manager
from config import config
from ui.utils.lakebase import is_lakebase_connected
from ui.utils.cache import cached_state

logger = logging.getLogger(__name__)


# Removed _is_lakebase_connected - now using shared utility from ui.utils.lakebase


@st.dialog("Save Progress", icon=":material/save:")
def show_save_dialog():
    """
    Material Design save dialog with session selection and overwrite capability.
    Allows user to create new session or overwrite existing one.
    """
    state = get_state_manager()
    
    # Fetch existing sessions for selection (cached for 30 seconds)
    existing_sessions = []
    try:
        # Use StateManager method instead of direct persistence access (cached)
        all_sessions = cached_state(
            "history_save_sessions",
            lambda: state.list_sessions(limit=10),
            ttl_seconds=30
        )
        if all_sessions:
            # Exclude current session from overwrite options
            existing_sessions = [s for s in all_sessions if s['session_key'] != state.session_key]
    except Exception as e:
        logger.error(f"Failed to load sessions: {e}", exc_info=True)
    
    # Session selection
    st.markdown("**Session Action**")
    
    # Build radio options
    radio_options = ["Create new session"]
    session_map = {}  # Map display name to session data
    
    for idx, session in enumerate(existing_sessions[:5]):  # Limit to 5 most recent
        session_name = session.get('session_name') or f"Session {idx + 1}"
        saved_at = session.get('last_saved_at', '')[:10] if session.get('last_saved_at') else ''
        display_name = f"{session_name} (saved {saved_at})"
        radio_options.append(display_name)
        session_map[display_name] = session
    
    selected_option = st.radio(
        "Choose action",
        options=radio_options,
        index=0,
        label_visibility="collapsed",
        key="save_dialog_session_selection"
    )
    
    # Determine if overwriting
    is_overwrite = selected_option != "Create new session"
    selected_session = session_map.get(selected_option) if is_overwrite else None
    
    st.divider()
    
    # Session name input
    st.markdown("**Session Name** (optional)")
    default_name = selected_session.get('session_name', '') if selected_session else ''
    session_name = st.text_input(
        "Give this session a memorable name",
        value=default_name,
        placeholder="My AdTech Tables",
        label_visibility="collapsed",
        help="Makes it easier to find this session later",
        key="save_dialog_session_name"
    )
    
    # Show overwrite warning
    if is_overwrite:
        st.warning(
            "⚠️ This will overwrite the existing session",
            icon=":material/warning:"
        )
    
    # Info message - YAMLs always saved to library
    st.info(
        "✓ Completed YAMLs will be automatically saved to library",
        icon=":material/library_add:"
    )
    
    st.divider()
    
    # What will be saved (Material info card)
    completed_count = len(state.get_completed_tables())
    queue_count = len(state.get_table_queue())
    has_table_interview = state.get_table_interview() is not None
    has_genie_interview = state.get_genie_interview() is not None
    
    st.info("**What will be saved:**", icon=":material/info:")
    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("Tables", completed_count, help="Completed table comments")
    with col2:
        items = []
        if queue_count > 0:
            items.append(f"• {queue_count} tables in queue")
        if has_table_interview:
            items.append("• In-progress table interview")
        if has_genie_interview:
            items.append("• In-progress Genie interview")
        if not items:
            items.append("• Current workflow state")
        
        for item in items:
            st.caption(item)
    
    st.divider()
    
    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel", type="secondary", use_container_width=True, key="save_dialog_cancel"):
            st.rerun()
    with col2:
        button_label = "Update Session" if is_overwrite else "Save Progress"
        button_icon = ":material/update:" if is_overwrite else ":material/save:"
        
        if st.button(
            button_label,
            type="primary",
            use_container_width=True,
            icon=button_icon,
            help="Save to Lakebase",
            key="save_dialog_confirm"
        ):
            with st.spinner("Saving..."):
                target_key = selected_session['session_key'] if is_overwrite else None
                session_id = state.save_progress(
                    session_name=session_name or None,
                    add_to_library=True,  # Always save to library
                    target_session_key=target_key
                )
                
                if session_id:
                    action = "updated" if is_overwrite else "saved"
                    st.toast(f"Progress {action}!", icon=":material/check_circle:")
                else:
                    st.toast("Failed to save - check Lakebase connection", icon=":material/error:")
            
            st.rerun()


@st.dialog("Rename Session", icon=":material/edit:")
def show_rename_dialog(session: dict):
    """Material Design rename dialog."""
    state = get_state_manager()
    
    session_name = session.get('name') or ''
    session_key = session['session_key']
    
    st.markdown(f"**Current name:** {session_name or '(Unnamed)'}")
    
    new_name = st.text_input(
        "New session name",
        value=session_name,
        placeholder="My AdTech Tables",
        key="rename_session_name"
    )
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel", type="secondary", use_container_width=True, key="rename_cancel"):
            st.rerun()
    with col2:
        if st.button(
            "Rename",
            type="primary",
            use_container_width=True,
            icon=":material/check:",
            key="rename_confirm"
        ):
            if new_name.strip():
                success = state.rename_session(session_key, new_name.strip())
                if success:
                    st.toast("Session renamed!", icon=":material/check_circle:")
                    st.rerun()
                else:
                    st.toast("Failed to rename session", icon=":material/error:")
            else:
                st.warning("Session name cannot be empty")


@st.dialog("Delete Session?", icon=":material/warning:")
def show_delete_dialog(session: dict):
    """Material Design delete confirmation dialog."""
    state = get_state_manager()
    
    session_name = session.get('name') or 'Unnamed Session'
    session_key = session['session_key']
    table_count = session.get('table_count', 0)
    
    st.markdown(f"**Session:** {session_name}")
    st.error("⚠️ This action cannot be undone!", icon=":material/error:")
    
    st.divider()
    
    st.info(f"This will delete:\n- Session: {session_name}\n- {table_count} table YAMLs\n- All associated data", icon=":material/info:")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel", type="secondary", use_container_width=True, key="delete_cancel"):
            st.rerun()
    with col2:
        if st.button(
            "Delete Session",
            type="primary",
            use_container_width=True,
            icon=":material/delete:",
            key="delete_confirm"
        ):
            success = state.delete_session(session_key)
            if success:
                st.toast("Session deleted", icon=":material/check_circle:")
                st.rerun()
            else:
                st.toast("Failed to delete session", icon=":material/error:")


@st.dialog("Restore Previous Session?", icon=":material/warning:")
def show_restore_dialog(session: dict):
    """Material Design restore confirmation dialog."""
    state = get_state_manager()
    
    session_name = session.get('name') or 'Unnamed Session'
    saved_at = session.get('saved_at', '')[:16] if session.get('saved_at') else 'Unknown'
    workflow = session.get('workflow_step', 'unknown')
    table_count = session.get('table_count', 0)
    
    st.markdown(f"**Session:** {session_name}")
    st.caption(f"Saved: {saved_at}")
    
    st.divider()
    
    # What will happen (Material info boxes)
    st.markdown("**This will:**")
    st.error("Current unsaved work will be lost!", icon=":material/error:")
    
    col1, col2 = st.columns(2)
    with col1:
        current_count = len(state.get_table_queue())
        st.metric("Current Work", f"{current_count} tables", help="Will be replaced")
    with col2:
        st.metric("Restored", f"{table_count} tables", help="From saved session")
    
    workflow_labels = {
        'browse': 'Selecting tables',
        'table_interview': 'Documenting',
        'review': 'Reviewing',
        'genie_interview': 'Genie Setup',
        'export': 'Export Ready'
    }
    workflow_label = workflow_labels.get(workflow, workflow)
    st.info(f"Workflow: **{workflow_label}**", icon=":material/route:")
    
    st.divider()
    
    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel", type="secondary", use_container_width=True, key="restore_cancel"):
            st.rerun()
    with col2:
        if st.button(
            "Restore Session",
            type="primary",
            use_container_width=True,
            icon=":material/restore:",
            key="restore_confirm"
        ):
            _do_restore(session['session_key'])


def _do_restore(session_key: str):
    """Actually restore the session."""
    state = get_state_manager()
    
    with st.spinner("Restoring session..."):
        success = state.restore_from_session(session_key)
        
        if success:
            st.toast("Session restored!", icon=":material/check_circle:")
            
            # Set flag so interview renderers can add resume context once
            st.session_state._session_just_restored = True
            
            # Clear state manager to force reload
            if "_state_manager" in st.session_state:
                del st.session_state._state_manager
            
            st.rerun()
        else:
            st.toast("Failed to restore session", icon=":material/error:")


def render_save_progress_button():
    """
    Render the Save Progress button in the sidebar.
    Only shown when Lakebase is connected.
    """
    if not is_lakebase_connected():
        return
    
    state = get_state_manager()
    unsaved_count = state.get_unsaved_count()
    
    # Show unsaved changes indicator
    if unsaved_count > 0:
        st.warning(
            f"{unsaved_count} unsaved change{'s' if unsaved_count != 1 else ''}",
            icon=":material/warning:"
        )
        button_label = f"Save Progress ({unsaved_count})"
        button_type = "primary"
    else:
        button_label = "Save Progress"
        button_type = "secondary"
    
    # Save Progress button
    if st.button(
        button_label,
        type=button_type,
        use_container_width=True,
        icon=":material/save:",
        help="Save your current progress to cloud storage",
        key="sidebar_save_progress_button"
    ):
        show_save_dialog()


def render_history_panel():
    """
    Render the session history panel with restore capability.
    Shows current session and saved sessions with Material Design.
    """
    state = get_state_manager()
    session_info = state.get_session_summary()
    
    with st.expander("Session History", expanded=False, icon=":material/history:"):
        # Current session (Material card style)
        st.markdown("**Current Session**")
        
        workflow_labels = {
            'browse': 'Selecting tables',
            'table_interview': 'Documenting tables',
            'review': 'Reviewing',
            'genie_interview': 'Configuring Genie',
            'export': 'Ready to export'
        }
        
        current_workflow = session_info.get('workflow_step', 'browse')
        workflow_label = workflow_labels.get(current_workflow, current_workflow)
        
        # Current session info - consolidated for compact display
        started = session_info.get('session_start', 'unknown')[:10]  # Just date
        queued = session_info.get('tables_in_queue', 0)
        completed = session_info.get('tables_completed', 0)
        st.caption(f"Started {started} • {queued} queued • {completed} done")
        st.info(workflow_label, icon=":material/edit_note:")
        
        # Previous sessions (only when Lakebase is enabled)
        if config.lakebase_enabled:
            st.divider()
            st.markdown("**Previous Sessions**")
            
            try:
                # Use StateManager method instead of direct persistence access (cached)
                sessions = cached_state(
                    "history_panel_sessions",
                    lambda: state.list_sessions(limit=10),
                    ttl_seconds=30
                )
                if not sessions:
                    st.caption("_Lakebase not connected_")
                    return
                
                # Filter out current session
                current_key = state.session_key
                previous_sessions = [s for s in sessions if s['session_key'] != current_key]
                
                if previous_sessions:
                    for session in previous_sessions[:5]:
                        _render_session_card(session)
                else:
                    st.caption("_No saved sessions yet_")
                    
            except Exception as e:
                st.caption(f"_Could not load sessions: {str(e)}_")
                logger.error(f"Failed to load sessions: {e}", exc_info=True)


def _render_session_card(session: dict):
    """Render a single session card with Material Design - compact layout."""
    session_name = session.get('name')
    session_key = session['session_key']
    saved_at = session.get('saved_at', '')[:10] if session.get('saved_at') else 'Unknown'
    table_count = session.get('table_count', 0)
    workflow = session.get('workflow_step', 'unknown')
    
    workflow_labels = {
        'browse': 'Browsing',
        'table_interview': 'Documenting',
        'review': 'Reviewing',
        'genie_interview': 'Genie Setup',
        'export': 'Export Ready'
    }
    workflow_label = workflow_labels.get(workflow, workflow or 'Unknown')
    
    # Material card layout with action buttons
    with st.container():
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            display_name = session_name if session_name else f"Session {saved_at}"
            st.markdown(f"**{display_name}**")
            st.caption(f"{saved_at} • {table_count} tables • {workflow_label}")
        
        with col2:
            # Restore button
            if st.button(
                "",
                key=f"restore_{session_key}",
                icon=":material/restore:",
                help="Restore this session"
            ):
                show_restore_dialog(session)
        
        with col3:
            # Rename button
            if st.button(
                "",
                key=f"rename_{session_key}",
                icon=":material/edit:",
                help="Rename this session"
            ):
                show_rename_dialog(session)
        
        with col4:
            # Delete button
            if st.button(
                "",
                key=f"delete_{session_key}",
                icon=":material/delete:",
                help="Delete this session"
            ):
                show_delete_dialog(session)