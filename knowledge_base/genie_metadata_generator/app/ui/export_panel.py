"""
Export Panel - Export all generated table comments and Genie metadata
Provides download options for individual files or bulk ZIP.
Material Design styling with flat icons.
"""

import io
import zipfile
from datetime import datetime

import streamlit as st
from config import config
from state import get_state_manager
from ui.constants import BUTTON_BACK_TO_REVIEW, BUTTON_BACK_TO_SELECT, BUTTON_DOWNLOAD_ZIP, ICON_BACK, ICON_FOLDER_ZIP
from ui.utils.cache import cached_state


def render_export():
    """Export all generated YAMLs."""
    state = get_state_manager()

    st.markdown("#### :material/download: Export Metadata")

    # Check if there are completed tables (cached with invalidation)
    completed_tables = cached_state(
        "export_completed_tables",
        lambda: state.get_completed_tables(),
        invalidate_on=['completed_table_count']
    )
    if not completed_tables:
        st.warning("No completed tables to export.")
        if st.button(BUTTON_BACK_TO_SELECT, use_container_width=True, icon=ICON_BACK):
            state.set_workflow_step('browse')
            st.session_state['selected_page'] = 'Select'
            st.rerun()
        return

    skip_genie = state.get_skip_genie()
    tier2_yaml = state.get_tier2_yaml()

    st.caption(f"Export {len(completed_tables)} table comments" +
               (" and Genie space metadata" if not skip_genie and tier2_yaml else ""))

    st.divider()

    # Tier 1 exports (per table)
    st.markdown("**Tier 1: Table Comments**")
    st.caption("Unity Catalog table comments (one per table)")

    for idx, table_data in enumerate(completed_tables):
        with st.expander(f"**{table_data['table']}** - {table_data['catalog']}.{table_data['schema']}", expanded=False, icon=":material/description:"):
            st.code(table_data['tier1_yaml'], language="yaml")

            col1, col2 = st.columns([1, 3])
            with col1:
                st.download_button(
                    "Download YAML",
                    data=table_data['tier1_yaml'],
                    file_name=f"{table_data['table']}_comment.yml",
                    mime="text/yaml",
                    key=f"download_tier1_{idx}",
                    use_container_width=True
                )
            with col2:
                # Handle missing timestamp (e.g., from restored sessions)
                timestamp = table_data.get('timestamp', 'Unknown')
                st.caption(f"Completed: {timestamp}")

    # Tier 2 export (single file for all tables)
    if not skip_genie and tier2_yaml:
        st.divider()
        st.markdown("**Tier 2: Genie Space Metadata**")
        st.caption("Query-optimized metadata for all tables in the Genie space")

        with st.expander("View Genie Metadata YAML", expanded=False, icon=":material/auto_awesome:"):
            st.code(tier2_yaml, language="yaml")

        st.download_button(
            "Download Genie Metadata YAML",
            data=tier2_yaml,
            file_name=f"genie_space_metadata_{datetime.now().strftime('%Y%m%d_%H%M')}.yml",
            mime="text/yaml",
            type="primary",
            use_container_width=True
        )

    # Bulk download option
    st.divider()
    st.markdown("**Bulk Export**")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.caption("Download all YAMLs as a ZIP archive")

        if st.button(BUTTON_DOWNLOAD_ZIP, type="secondary", use_container_width=True, icon=ICON_FOLDER_ZIP):
            # Create ZIP file in memory
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add Tier 1 YAMLs
                for table_data in completed_tables:
                    filename = f"tier1_table_comments/{table_data['table']}_comment.yml"
                    zip_file.writestr(filename, table_data['tier1_yaml'])

                # Add Tier 2 YAML if available
                if not skip_genie and tier2_yaml:
                    zip_file.writestr("tier2_genie_metadata/genie_space_metadata.yml", tier2_yaml)

                # Add a README
                readme_content = f"""# Genie Metadata Export
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Contents

### Tier 1: Table Comments (Unity Catalog)
{len(completed_tables)} table comment files in `tier1_table_comments/`

Tables documented:
{chr(10).join(f"- {t['catalog']}.{t['schema']}.{t['table']}" for t in completed_tables)}

### Tier 2: Genie Space Metadata
{'Included in `tier2_genie_metadata/genie_space_metadata.yml`' if not skip_genie and tier2_yaml else 'Not generated'}

## Usage

1. **Apply Table Comments to Unity Catalog:**
   Use Databricks CLI or SQL to apply table comments:
   ```sql
   COMMENT ON TABLE catalog.schema.table_name IS '<comment_from_yaml>';
   ```

2. **Configure Genie Space:**
   Upload the Genie metadata YAML to your Genie space configuration.

## Documentation
See: https://docs.databricks.com/genie/
"""
                zip_file.writestr("README.md", readme_content)

            zip_buffer.seek(0)

            st.toast("ZIP file ready!", icon=":material/folder_zip:")

            st.download_button(
                "Download ZIP File",
                data=zip_buffer,
                file_name=f"genie_metadata_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
                mime="application/zip",
                use_container_width=True
            )

    with col2:
        # Summary
        st.info(f"""
**Export Summary:**
- {len(completed_tables)} table comments
- {'Yes' if not skip_genie and tier2_yaml else 'No'} Genie metadata
        """, icon=":material/info:")

    # Save to YAML Library (Material Design expander)
    st.divider()
    _render_save_to_library_section(completed_tables, tier2_yaml, skip_genie)

    # Next steps instructions
    st.divider()
    st.markdown("**Next Steps**")

    with st.expander("How to apply these to Databricks", expanded=True, icon=":material/help:"):
        st.markdown("""
### 1. Apply Table Comments to Unity Catalog

Use the Databricks SQL Editor or CLI:

```sql
-- For each table, extract the 'comment' field from the YAML and apply:
COMMENT ON TABLE catalog.schema.table_name IS 'Your table description here';
```

### 2. Configure Genie Space

1. Navigate to your Databricks Genie space
2. Upload the Genie metadata YAML or copy its contents
3. Configure the space with the instructions and examples

### 3. Test with Genie

Try these example queries in your Genie space:
- "Show me total revenue for last month"
- "Which customers placed the most orders?"
- "What's the trend in sales over time?"

### Documentation
- [Genie Best Practices](https://docs.databricks.com/genie/best-practices.html)
- [Unity Catalog Comments](https://docs.databricks.com/sql/language-manual/sql-ref-syntax-ddl-comment.html)
        """)

    # Action buttons
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Start New Session", type="secondary", use_container_width=True, icon=":material/refresh:"):
            # Reset all session state using StateManager
            state.reset_session()
            st.success("Session cleared! Ready to start fresh.", icon=":material/check_circle:")
            st.rerun()

    with col2:
        if st.button(BUTTON_BACK_TO_REVIEW, use_container_width=True, icon=ICON_BACK):
            state.set_workflow_step('review')
            st.session_state['selected_page'] = 'Review'
            st.rerun()


def _render_save_to_library_section(completed_tables, tier2_yaml, skip_genie):
    """Render Save to Library section with Material Design."""
    # Only show if Lakebase is enabled
    if not config.lakebase_enabled:
        return

    from state.services import get_library_service
    state = get_state_manager()
    library_service = get_library_service(state.user_email)

    # Check if actually available (may be disabled or connection failed)
    if not library_service.is_available():
        st.warning(
            "Library unavailable: Lakebase connection failed",
            icon=":material/warning:"
        )
        return

    with st.expander(
        "Save to YAML Library",
        expanded=True,
        icon=":material/library_add:"
    ):
        st.caption("Save these YAMLs for easy reuse with similar tables")

        add_to_library = st.checkbox(
            "Add these YAMLs to your library",
            help="Save YAMLs for reuse with similar tables",
            key="export_add_to_library"
        )

        if add_to_library:
            tags_input = st.text_input(
                "Tags (comma-separated)",
                placeholder="analytics, sales, customer-data",
                help="Add tags to organize your YAMLs",
                key="export_library_tags"
            )

            st.divider()

            # Summary (Material metrics)
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "Table YAMLs",
                    len(completed_tables),
                    help="Table comment YAMLs"
                )
            with col2:
                genie_count = 1 if (not skip_genie and tier2_yaml) else 0
                st.metric(
                    "Genie Spaces",
                    genie_count,
                    help="Genie space configurations"
                )

            st.info(
                "Access anytime in Library tab",
                icon=":material/library_books:"
            )

            st.divider()

            # Save button
            if st.button(
                "Save to Library",
                type="primary",
                use_container_width=True,
                icon=":material/library_add:",
                key="export_save_to_library_btn"
            ):
                with st.spinner("Saving to library..."):
                    # Parse tags
                    tags = [tag.strip() for tag in tags_input.split(',')
                           if tag.strip()] if tags_input else None

                    saved_count = library_service.save_yamls(
                        completed_tables=completed_tables,
                        genie_yaml=tier2_yaml,
                        skip_genie=skip_genie,
                        tags=tags
                    )

                    if saved_count > 0:
                        st.toast(
                            f"Saved {saved_count} YAML{'s' if saved_count != 1 else ''} to library!",
                            icon=":material/check_circle:"
                        )
                    else:
                        st.warning("Failed to save to library", icon=":material/warning:")
