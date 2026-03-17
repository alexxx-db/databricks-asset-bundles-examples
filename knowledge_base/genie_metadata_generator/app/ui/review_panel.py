"""
Review Panel - Review completed table comments before Genie interview
Allows editing, downloading, and deciding on next steps.
Material Design styling with flat icons.
"""

import streamlit as st
from state import get_state_manager, TableIdentifier
from ui.utils.navigation import render_back_button
from ui.utils.cache import cached_state
from ui.constants import (
    BUTTON_ADD_MORE_TABLES,
    BUTTON_BACK_TO_SELECT,
    ICON_ADD
)
from ui.utils.formatting import format_completed_status
from ui.content.help_content import WHATS_NEXT_REVIEW


def render_review():
    """Review all completed table comments before Genie interview."""
    state = get_state_manager()
    
    st.markdown("#### :material/rate_review: Review Table Comments")
    
    # Check if there are completed tables (cached with invalidation)
    completed_tables = cached_state(
        "review_completed_tables",
        lambda: state.get_completed_tables(),
        invalidate_on=['completed_table_count']
    )
    if not completed_tables:
        st.info("No tables have been documented yet.")
        render_back_button('browse', label=BUTTON_BACK_TO_SELECT)
        return
    
    st.caption(f"{format_completed_status(len(completed_tables))}. Review and edit if needed, then proceed to Genie or export.")
    
    # Add tips for first-time users
    if len(completed_tables) <= 3:
        with st.expander("What's Next?", icon=":material/help:", expanded=True):
            st.markdown(WHATS_NEXT_REVIEW)
    
    st.divider()
    
    # Display all completed tables
    for idx, table_data in enumerate(completed_tables):
        table_name = f"{table_data['catalog']}.{table_data['schema']}.{table_data['table']}"
        
        with st.expander(f"**{table_data['table']}** - {table_name}", expanded=False, icon=":material/description:"):
            # Handle missing timestamp (e.g., from restored sessions)
            timestamp = table_data.get('timestamp', 'Unknown')
            st.caption(f"Completed: {timestamp}")
            
            # Show Tier 1 YAML preview
            st.markdown("**Table Comment YAML:**")
            yaml_preview = table_data['tier1_yaml']
            if len(yaml_preview) > 800:
                st.code(yaml_preview[:800] + "\n\n... (truncated, download to see full content)", language="yaml")
            else:
                st.code(yaml_preview, language="yaml")
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Edit", key=f"edit_{idx}", use_container_width=True, icon=":material/edit:"):
                    # Save to library first if Lakebase is available, then navigate to Editor
                    from config import config
                    
                    if config.lakebase_enabled:
                        from state.services import get_library_service
                        library_service = get_library_service(state.user_email)
                        
                        if library_service.is_available():
                            # Save this table YAML to library
                            saved_count = library_service.save_yamls(
                                completed_tables=[table_data],
                                skip_genie=True
                            )
                            
                            if saved_count > 0:
                                # Need to get the yaml_id from library after saving
                                # Search for the YAML we just saved
                                yamls = library_service.get_yamls(yaml_type='table_comment', limit=100)
                                matching_yaml = None
                                for yaml_item in yamls:
                                    if (yaml_item['catalog'] == table_data['catalog'] and
                                        yaml_item['schema'] == table_data['schema'] and
                                        yaml_item['table_name'] == table_data['table']):
                                        matching_yaml = yaml_item
                                        break
                                
                                if matching_yaml:
                                    # Navigate to editor with library ID
                                    st.session_state['editor_yaml_id'] = matching_yaml['id']
                                    st.session_state['selected_page'] = 'Editor'
                                    st.toast("Opening in editor", icon=":material/edit:")
                                    st.rerun()
                                else:
                                    st.error("Saved but could not find YAML in library", icon=":material/error:")
                            else:
                                st.error("Failed to save to library", icon=":material/error:")
                        else:
                            st.warning("Lakebase not available. Cannot edit YAMLs.", icon=":material/warning:")
                            st.caption("Enable Lakebase to use the YAML editor")
                    else:
                        st.warning("YAML Editor requires Lakebase to be enabled", icon=":material/warning:")
                        st.caption("Enable Lakebase in settings to edit YAMLs")
            
            with col2:
                st.download_button(
                    "Download",
                    data=yaml_preview,
                    file_name=f"{table_data['table']}_comment.yml",
                    mime="text/yaml",
                    key=f"download_{idx}",
                    use_container_width=True
                )
            
            with col3:
                # Check if this table is pending deletion using StateManager
                is_pending = state.is_pending_delete(idx)
                
                if not is_pending:
                    if st.button("Remove", key=f"remove_{idx}", use_container_width=True, icon=":material/delete:"):
                        state.set_pending_delete(idx, True)
                        st.rerun()
                else:
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("Confirm", key=f"confirm_{idx}", type="secondary", use_container_width=True, icon=":material/check:"):
                            state.remove_completed_table(idx)
                            state.clear_all_pending_deletes()
                            st.toast("Table removed", icon=":material/delete:")
                            st.rerun()
                    with col_b:
                        if st.button("Cancel", key=f"cancel_{idx}", use_container_width=True, icon=":material/close:"):
                            state.clear_pending_delete(idx)
                            st.rerun()
    
    st.divider()
    
    # Summary stats
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Tables Documented", len(completed_tables))
    with col2:
        # Count profiled tables
        profiled_count = 0
        for t in completed_tables:
            if t.get('profile_key'):
                table_id = TableIdentifier(
                    catalog=t['catalog'],
                    schema=t['schema'],
                    table=t['table']
                )
                if state.has_profile(table_id):
                    profiled_count += 1
        st.metric("With Data Profile", profiled_count)
    
    st.divider()
    
    # Action buttons
    st.markdown("**Next Steps**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button(BUTTON_ADD_MORE_TABLES, use_container_width=True, icon=ICON_ADD):
            state.set_workflow_step('browse')
            st.session_state['selected_page'] = 'Select'
            st.rerun()
    
    with col2:
        if st.button("Export Comments Only", type="secondary", use_container_width=True, icon=":material/download:"):
            # Skip Genie interview, go straight to export
            state.set_skip_genie(True)
            state.set_workflow_step('export')
            st.session_state['selected_page'] = 'Export'
            st.rerun()
    
    with col3:
        if st.button("Configure Genie", type="primary", use_container_width=True, icon=":material/auto_awesome:"):
            # Proceed to Genie interview
            state.set_skip_genie(False)
            state.set_workflow_step('genie_interview')
            st.session_state['selected_page'] = 'Genie'
            st.rerun()
    
    st.caption("Configure Genie Space to optimize these tables for natural language queries in Databricks Genie.")
