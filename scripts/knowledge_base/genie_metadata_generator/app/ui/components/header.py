"""
Settings panel component for sidebar.
Navigation is now handled by streamlit-navigation-bar in app.py.
Material Design styling with flat icons.
Save Progress functionality has been moved to Session History panel.
"""

import streamlit as st
from config import config
from state import get_state_manager


def _get_lakebase_status() -> tuple[str, str]:
    """Check actual Lakebase connection status."""
    if not config.lakebase_enabled:
        return ('info', 'In-Memory')

    try:
        from state.db import get_connection_status
        status = get_connection_status()

        if status.get('connected'):
            return ('success', 'Lakebase Connected')
        else:
            return ('warning', 'DB Offline')
    except Exception:
        return ('warning', 'DB Error')


def render_settings_panel():
    """
    Render settings panel for the sidebar.
    Shows session info, storage status, user config, and session controls.
    Uses Material icons.
    Note: Save Progress has been moved to Session History panel.
    """
    state = get_state_manager()
    session_info = state.get_session_summary()
    status_type, status_msg = _get_lakebase_status()

    with st.expander("Settings", expanded=False, icon=":material/settings:"):
        # Storage status with session info embedded for compact display
        queued = session_info.get('tables_in_queue', 0)
        completed = session_info.get('tables_completed', 0)
        status_with_info = f"{queued} queued • {completed} done | {status_msg}"

        if status_type == 'success':
            st.success(status_with_info, icon=":material/cloud_done:")
        elif status_type == 'warning':
            st.warning(status_with_info, icon=":material/warning:")
        else:
            st.info(status_with_info, icon=":material/memory:")

        st.divider()

        # Config info
        st.markdown("**Config**")
        user_email = session_info.get('user_email', 'unknown')
        st.caption(f"User: {user_email}")
        st.caption(f"LLM: `{config.llm_endpoint_name or 'Not set'}`")

        st.divider()

        # Reset button
        if st.button("Reset Session", use_container_width=True, type="secondary", icon=":material/refresh:"):
            state.reset_session()
            st.rerun()
