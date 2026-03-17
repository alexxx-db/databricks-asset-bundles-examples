"""
Dedicated YAML Editor Page
Full-width editor for viewing and editing YAML files from the library with version control.
"""

import streamlit as st
from state import get_state_manager
from config import config
from utils.yaml_utils import validate_yaml
from ui.utils.cache import cached_state
import logging

logger = logging.getLogger(__name__)


def render_yaml_editor_page():
    """
    Render dedicated YAML editor page with library integration.
    Provides full-width layout for comfortable editing of large YAML files.
    """
    if not config.lakebase_enabled:
        st.warning("YAML Editor requires Lakebase to be enabled", icon=":material/warning:")
        return
    
    try:
        from state.services import get_library_service
        
        state = get_state_manager()
        library_service = get_library_service(state.user_email)
        
        if not library_service.is_available():
            st.error("Lakebase connection not available", icon=":material/error:")
            return
        
        # Compact page header
        st.markdown("#### :material/edit_document: YAML Editor")
        
        # Check if we have a YAML ID to load (from navigation)
        yaml_id_to_load = st.session_state.get('editor_yaml_id', None)
        
        # Get all YAMLs for selector (cached for 60 seconds)
        all_yamls = cached_state(
            "editor_library_yamls",
            lambda: library_service.get_yamls(limit=100),
            ttl_seconds=60,
            invalidate_on=['_yaml_saved', '_yaml_deleted']
        )
        
        if not all_yamls:
            st.info("No YAMLs in library yet. Create table comments or Genie spaces first.", icon=":material/info:")
            return
        
        # Create options for selectbox
        yaml_options = {}
        for yaml_item in all_yamls:
            yaml_type = "Table" if yaml_item['yaml_type'] == 'table_comment' else "Genie"
            label = f"[{yaml_type}] {yaml_item['table_name']} ({yaml_item['catalog']}.{yaml_item['schema']})"
            yaml_options[label] = yaml_item
        
        # If we have a yaml_id to load, find its index
        default_index = 0
        if yaml_id_to_load:
            for idx, (label, item) in enumerate(yaml_options.items()):
                if item['id'] == yaml_id_to_load:
                    default_index = idx
                    break
            # Clear the session state after using it
            del st.session_state['editor_yaml_id']
        
        # File selector - compact
        selected_label = st.selectbox(
            "Select YAML to edit",
            options=list(yaml_options.keys()),
            index=default_index,
            key="yaml_selector",
            label_visibility="collapsed"
        )
        
        current_yaml = yaml_options[selected_label]
        
        # Metadata in horizontal collapsable expander
        with st.expander("📋 Metadata", expanded=False):
            meta_cols = st.columns(6)
            with meta_cols[0]:
                st.caption("**Table**")
                st.text(current_yaml['table_name'])
            with meta_cols[1]:
                st.caption("**Catalog**")
                st.text(current_yaml['catalog'])
            with meta_cols[2]:
                st.caption("**Schema**")
                st.text(current_yaml['schema'])
            with meta_cols[3]:
                st.caption("**Type**")
                st.text("Table" if current_yaml['yaml_type'] == 'table_comment' else "Genie")
            with meta_cols[4]:
                st.caption("**Updated**")
                st.text(current_yaml['updated_at'][:10] if current_yaml['updated_at'] else 'Unknown')
            with meta_cols[5]:
                st.caption("**Tags**")
                if current_yaml.get('tags'):
                    st.text(", ".join(current_yaml['tags']))
                else:
                    st.text("None")
        
        # Initialize edited content in session state if not present
        editor_key = f"yaml_editor_{current_yaml['id']}"
        history_key = f"yaml_history_{current_yaml['id']}"
        
        if editor_key not in st.session_state:
            st.session_state[editor_key] = current_yaml['yaml_content']
        
        # Initialize edit history (max 10 edits)
        if history_key not in st.session_state:
            st.session_state[history_key] = []
        
        # Check if content has changed
        has_changes = st.session_state[editor_key] != current_yaml['yaml_content']
        
        # Validation
        is_valid, error_msg = validate_yaml(st.session_state[editor_key])
        
        # Validation status row - above editor
        status_col1, status_col2 = st.columns([1, 1])
        with status_col1:
            if is_valid:
                st.success("✓ Valid YAML syntax", icon=":material/check_circle:")
            else:
                st.error(f"✗ Invalid YAML: {error_msg}", icon=":material/error:")
        with status_col2:
            if has_changes:
                st.warning("⚠ Unsaved changes", icon=":material/edit:")
            else:
                st.info("✓ No changes", icon=":material/check:")
        
        # YAML editor - maximum height
        edited_content = st.text_area(
            "YAML Content",
            value=st.session_state[editor_key],
            height=800,
            key=f"yaml_text_{current_yaml['id']}",
            label_visibility="collapsed",
            help="Edit YAML content. Changes are validated in real-time."
        )
        
        # Track edit history (only on actual changes)
        if edited_content != st.session_state[editor_key]:
            # Store previous state in history
            st.session_state[history_key].append(st.session_state[editor_key])
            # Keep only last 10 edits
            if len(st.session_state[history_key]) > 10:
                st.session_state[history_key].pop(0)
        
        # Update session state
        st.session_state[editor_key] = edited_content
        
        # Re-validate after edit
        has_changes = edited_content != current_yaml['yaml_content']
        is_valid, error_msg = validate_yaml(edited_content)
        
        # Action buttons row - below editor
        btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns([1, 1, 1, 1, 5])
        
        with btn_col1:
            # Undo button
            if st.button("↶ Undo", use_container_width=True, disabled=len(st.session_state[history_key]) == 0):
                if st.session_state[history_key]:
                    previous = st.session_state[history_key].pop()
                    st.session_state[editor_key] = previous
                    st.rerun()
        
        with btn_col2:
            # Revert to original button
            if st.button("⟲ Revert", use_container_width=True, disabled=not has_changes):
                st.session_state[editor_key] = current_yaml['yaml_content']
                st.session_state[history_key] = []
                st.rerun()
        
        with btn_col3:
            if st.download_button(
                "Download",
                data=current_yaml['yaml_content'],
                file_name=f"{current_yaml['table_name']}_{current_yaml['yaml_type']}.yml",
                mime="text/yaml",
                icon=":material/download:",
                use_container_width=True
            ):
                st.toast("YAML downloaded!", icon=":material/check_circle:")
        
        with btn_col4:
            # Delete button
            if st.button(
                "Delete",
                icon=":material/delete:",
                use_container_width=True,
                type="secondary"
            ):
                if library_service.delete_yaml(current_yaml['id']):
                    st.toast("Deleted from library", icon=":material/check_circle:")
                    st.rerun()
                else:
                    st.error("Failed to delete", icon=":material/error:")
        
        with btn_col5:
            # Save button
            if st.button(
                "Save",
                type="primary",
                icon=":material/save:",
                use_container_width=True,
                disabled=not (is_valid and has_changes)
            ):
                # Save the YAML using LibraryService (architecture compliance)
                try:
                    if library_service.update_yaml(current_yaml['id'], edited_content):
                        st.success("YAML saved successfully! New version created.", icon=":material/check_circle:")
                        # Update the current_yaml content to reflect saved state
                        current_yaml['yaml_content'] = edited_content
                        # Clear the editor session state to force reload
                        if editor_key in st.session_state:
                            del st.session_state[editor_key]
                        st.rerun()
                    else:
                        st.error("Failed to save YAML", icon=":material/error:")
                except Exception as e:
                    st.error(f"Error saving YAML: {str(e)}", icon=":material/error:")
                    logger.error(f"Error saving YAML: {e}", exc_info=True)
        
        # Show help text if there are changes
        if has_changes and is_valid:
            st.caption("💡 Click Save to commit changes and create a new version")
    
    except Exception as e:
        st.error(f"Error loading editor: {str(e)}", icon=":material/error:")
        logger.error(f"Editor error: {e}", exc_info=True)
