"""
YAML Library panel for browsing and reusing saved YAML configurations.
Material Design styling throughout.
"""

import logging
import streamlit as st
from state import get_state_manager
from utils.data_conversion import library_yaml_to_table_data
from ui.utils.cache import cached_state

logger = logging.getLogger(__name__)


def render_library_panel():
    """
    Main YAML library panel with Material Design.
    Allows users to browse, search, and reuse saved YAML configurations.
    Now with separate sections for Table Comments and Genie Spaces.
    """
    st.markdown("#### :material/library_books: YAML Library")
    st.caption("Your saved YAML configurations for reuse")
    
    from ui.utils.availability import check_lakebase_available, check_library_service_available
    
    # Check if Lakebase is enabled using utility
    if not check_lakebase_available("YAML Library requires Lakebase to be enabled"):
        return
    
    try:
        from state.services import get_library_service
        
        state = get_state_manager()
        library_service = get_library_service(state.user_email)
        
        # Check library service availability using utility
        if not check_library_service_available(library_service):
            return
        
        # Search bar (Material design)
        search = st.text_input(
            "Search YAMLs",
            placeholder="Search by table, catalog, or schema...",
            key="library_search"
        )
        
        st.divider()
        
        # Get all library items (cached for 60 seconds)
        if search:
            all_items = cached_state(
                f"library_search_{hash(search)}",
                lambda: library_service.search_yamls(search, limit=50),
                ttl_seconds=60
            )
            # Separate by type
            table_items = [item for item in all_items if item['yaml_type'] == 'table_comment']
            genie_items = [item for item in all_items if item['yaml_type'] == 'genie_space']
        else:
            table_items = cached_state(
                "library_table_yamls",
                lambda: library_service.get_yamls(yaml_type='table_comment', limit=50),
                ttl_seconds=60,
                invalidate_on=['_yaml_saved', '_yaml_deleted']
            )
            genie_items = cached_state(
                "library_genie_yamls",
                lambda: library_service.get_yamls(yaml_type='genie_space', limit=50),
                ttl_seconds=60,
                invalidate_on=['_yaml_saved', '_yaml_deleted']
            )
        
        # Render separate sections
        if not table_items and not genie_items:
            st.info("No YAMLs in library yet", icon=":material/info:")
            st.caption("YAMLs are automatically saved to library when you save progress")
            return
        
        # Table Comments Section
        _render_table_yaml_section(table_items, library_service)
        
        st.divider()
        
        # Genie Spaces Section
        _render_genie_yaml_section(genie_items, library_service)
            
    except Exception as e:
        st.error(f"Error loading library: {str(e)}", icon=":material/error:")
        logger.error(f"Failed to load library: {e}", exc_info=True)


def _render_table_yaml_section(table_items: list, library_service):
    """Render Table Comments section with actions."""
    st.markdown("### :material/description: Table Comments")
    
    if not table_items:
        st.caption("_No table comments in library yet_")
        return
    
    st.caption(f"{len(table_items)} table comment(s) saved")
    
    for yaml_item in table_items:
        _render_table_yaml_item(yaml_item, library_service)


def _render_genie_yaml_section(genie_items: list, library_service):
    """Render Genie Spaces section with actions."""
    st.markdown("### :material/auto_awesome: Genie Spaces")
    
    if not genie_items:
        st.caption("_No Genie spaces in library yet_")
        return
    
    st.caption(f"{len(genie_items)} Genie space(s) saved")
    
    for yaml_item in genie_items:
        _render_genie_yaml_item(yaml_item, library_service)


def _render_table_yaml_item(yaml_item: dict, library_service):
    """Render a single table YAML library item with edit/re-interview actions."""
    with st.expander(
        f"**{yaml_item['table_name']}** - {yaml_item['catalog']}.{yaml_item['schema']}",
        icon=":material/description:"
    ):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.caption(f"Saved: {yaml_item['updated_at'][:16] if yaml_item['updated_at'] else 'Unknown'}")
            
            # Tags as Material chips (HTML) - using CSS variables for dark mode support
            if yaml_item.get('tags'):
                st.markdown("**Tags:**")
                tags_html = " ".join([
                    f'<span style="background: var(--md-chip-bg, rgba(25,118,210,0.1)); '
                    f'padding: 4px 8px; border-radius: 12px; '
                    f'font-size: 12px; color: var(--md-chip-text, #1976D2);">{tag}</span>'
                    for tag in yaml_item['tags']
                ])
                st.markdown(tags_html, unsafe_allow_html=True)
        
        with col2:
            # Action buttons with Material icons
            if st.button(
                "Preview",
                key=f"preview_{yaml_item['id']}",
                icon=":material/visibility:",
                use_container_width=True
            ):
                # Navigate to editor page for full-width preview
                st.session_state['editor_yaml_id'] = yaml_item['id']
                st.session_state['selected_page'] = 'Editor'
                st.rerun()
            
            if st.button(
                "Re-interview",
                key=f"reinterview_{yaml_item['id']}",
                icon=":material/refresh:",
                use_container_width=True,
                help="Start new interview with this YAML as context"
            ):
                _handle_reinterview_table(yaml_item)
            
            if st.button(
                "Edit",
                key=f"edit_{yaml_item['id']}",
                icon=":material/edit:",
                use_container_width=True,
                help="Edit and update this YAML"
            ):
                _handle_edit_yaml(yaml_item, library_service)
            
            if st.download_button(
                "Download",
                data=yaml_item['yaml_content'],
                file_name=f"{yaml_item['table_name']}_comment.yml",
                mime="text/yaml",
                key=f"download_{yaml_item['id']}",
                icon=":material/download:",
                use_container_width=True
            ):
                st.toast("YAML downloaded", icon=":material/check_circle:")
            
            if st.button(
                "Delete",
                key=f"delete_{yaml_item['id']}",
                icon=":material/delete:",
                use_container_width=True,
                help="Remove from library"
            ):
                if library_service.delete_yaml(yaml_item['id']):
                    st.toast("Removed from library", icon=":material/check_circle:")
                    st.rerun()
                else:
                    st.toast("Failed to delete", icon=":material/error:")


def _render_genie_yaml_item(yaml_item: dict, library_service):
    """Render a single Genie YAML library item with edit/re-interview actions."""
    metadata = yaml_item.get('metadata', {})
    table_count = metadata.get('table_count', 0) if isinstance(metadata, dict) else 0
    
    with st.expander(
        f"**{yaml_item['table_name']}** - {table_count} tables",
        icon=":material/auto_awesome:"
    ):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.caption(f"Saved: {yaml_item['updated_at'][:16] if yaml_item['updated_at'] else 'Unknown'}")
            st.caption(f"Catalog: {yaml_item['catalog']}.{yaml_item['schema']}")
            
            # Tags as Material chips (HTML) - using CSS variables for dark mode support
            if yaml_item.get('tags'):
                st.markdown("**Tags:**")
                tags_html = " ".join([
                    f'<span style="background: var(--md-chip-bg, rgba(25,118,210,0.1)); '
                    f'padding: 4px 8px; border-radius: 12px; '
                    f'font-size: 12px; color: var(--md-chip-text, #1976D2);">{tag}</span>'
                    for tag in yaml_item['tags']
                ])
                st.markdown(tags_html, unsafe_allow_html=True)
        
        with col2:
            # Action buttons with Material icons
            if st.button(
                "Preview",
                key=f"preview_{yaml_item['id']}",
                icon=":material/visibility:",
                use_container_width=True
            ):
                # Navigate to editor page for full-width preview
                st.session_state['editor_yaml_id'] = yaml_item['id']
                st.session_state['selected_page'] = 'Editor'
                st.rerun()
            
            # Note: Re-interview for Genie spaces is not supported directly
            # Users should use "Select from Library" in the Genie page instead
            
            if st.button(
                "Edit",
                key=f"edit_{yaml_item['id']}",
                icon=":material/edit:",
                use_container_width=True,
                help="Edit and update this YAML"
            ):
                _handle_edit_yaml(yaml_item, library_service)
            
            if st.download_button(
                "Download",
                data=yaml_item['yaml_content'],
                file_name=f"{yaml_item['table_name']}_genie.yml",
                mime="text/yaml",
                key=f"download_{yaml_item['id']}",
                icon=":material/download:",
                use_container_width=True
            ):
                st.toast("YAML downloaded", icon=":material/check_circle:")
            
            if st.button(
                "Delete",
                key=f"delete_{yaml_item['id']}",
                icon=":material/delete:",
                use_container_width=True,
                help="Remove from library"
            ):
                if library_service.delete_yaml(yaml_item['id']):
                    st.toast("Removed from library", icon=":material/check_circle:")
                    st.rerun()
                else:
                    st.toast("Failed to delete", icon=":material/error:")


def _handle_reinterview_table(yaml_item: dict):
    """Handle re-interview action for table YAML."""
    state = get_state_manager()
    
    # Convert library YAML to table_data format using utility function
    table_data = library_yaml_to_table_data(yaml_item)
    
    # Set up queue with this table
    state.set_table_queue([table_data])
    state.set_current_table_index(0)
    state.clear_table_interview()  # Clear any existing interview
    
    # Navigate to interview
    state.set_workflow_step('table_interview')
    st.session_state['selected_page'] = 'Document'
    st.rerun()


def _handle_edit_yaml(yaml_item: dict, library_service):
    """Handle edit action for YAML - navigates to editor page."""
    # Store YAML ID in session state for editor to load
    st.session_state['editor_yaml_id'] = yaml_item['id']
    # Navigate to Editor page
    st.session_state['selected_page'] = 'Editor'
    st.rerun()


# Removed unused dialog functions:
# - show_yaml_edit_dialog() - Edit navigates to editor page instead
# - show_yaml_preview() - Preview navigates to editor page instead
# These functions were defined but never called in the codebase
