"""
Genify - Main Streamlit App
AI-powered table metadata generator for Databricks Genie.

Uses streamlit-navigation-bar for workflow navigation and sidebar for history.
Material Design inspired UI with flat monochrome icons.
"""

import streamlit as st
from config import config
from state import get_state_manager
from ui.table_browser import render_table_browser
from ui.review_panel import render_review
from ui.export_panel import render_export
from ui.yaml_library_panel import render_library_panel
from ui.split_screen_interview import render_table_interview_unified, render_genie_interview_unified
from ui.yaml_editor_page import render_yaml_editor_page
from ui.help_page import render_help_page
from ui.components import render_history_panel, render_settings_panel, render_save_progress_button
from ui.styles import inject_app_styles
import logging

# Configure logging for the app
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set LLM client to INFO level for detailed logging
logging.getLogger('llm.client').setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.info("="*80)
logger.info("Genify App Starting")
logger.info("="*80)


# Page configuration
st.set_page_config(
    page_title=config.page_title,
    page_icon=config.page_icon,
    layout=config.layout,
    initial_sidebar_state="auto"
)

# Inject global CSS styles (theme, layout, components)
inject_app_styles()


def initialize_session_state():
    """Initialize session state variables via StateManager."""
    state = get_state_manager()

    if '_initialized' not in st.session_state:
        session_info = state.get_session_summary()
        logger.info(f"Session initialized for user: {session_info['user']}")
        logger.info(f"Session key: {session_info['session_key']}")
        logger.info(f"Lakebase enabled: {config.lakebase_enabled}")

        # Log Lakebase connection status and ensure tables exist
        if config.lakebase_enabled:
            try:
                from state.db import get_connection_status
                from state.schema import ensure_genify_schema_exists
                from state.db import get_lakebase_connection_safe

                status = get_connection_status()
                if status.get('connected'):
                    logger.info(f"Lakebase connected: database={status.get('database')}, user={status.get('user')}, host={status.get('host')}")

                    # Proactively ensure all database tables exist at app startup
                    try:
                        conn = get_lakebase_connection_safe()
                        if conn:
                            ensure_genify_schema_exists(conn)
                            logger.info("✓ All Lakebase tables verified/created")
                    except Exception as schema_err:
                        logger.warning(f"Could not initialize Lakebase schema: {schema_err}")
                else:
                    logger.warning(f"Lakebase NOT connected: {status.get('error', 'Unknown error')}")
            except Exception as e:
                logger.error(f"Lakebase connection check failed: {e}")
        else:
            logger.info("Lakebase disabled - using in-memory session state")

        st.session_state._initialized = True


def render_sidebar():
    """Render the sidebar with logo, history, settings, and tips."""
    state = get_state_manager()
    workflow_step = state.get_workflow_step()

    with st.sidebar:
        # Logo at the top - Large and prominent with Material icon
        st.markdown('''
            <div style="text-align: center; padding: 1rem 0 0.5rem 0;" class="genify-logo-container">
                <h1 style="font-size: 32px; font-weight: 500; margin: 0; padding: 0; display: flex; align-items: center; justify-content: center; gap: 8px;" class="genify-logo">
                    <span style="font-size: 32px;">✨</span>
                    <span>Genify</span>
                </h1>
                <p style="font-size: 16px; margin-top: 0.5rem; margin-bottom: 0;" class="genify-tagline">Metadata generator for Unity Catalog</p>
            </div>
        ''', unsafe_allow_html=True)

        st.divider()

        # Interview Status Indicator - show if interview in progress
        table_interview = state.get_table_interview()
        genie_interview = state.get_genie_interview()

        if table_interview or genie_interview:
            st.warning("⚠️ Interview in Progress", icon=":material/edit_note:")

            interview_type = "Table" if table_interview else "Genie"
            active_interview = table_interview or genie_interview

            # Show progress
            current = active_interview.current_section_idx + 1
            total = len(active_interview.sections)
            progress_pct = int((current / total) * 100)

            st.caption(f"{interview_type} Interview: Section {current}/{total} ({progress_pct}%)")

            if st.button("▶️ Continue Interview", type="primary", use_container_width=True, key="sidebar_continue"):
                if table_interview:
                    st.session_state['selected_page'] = 'Document'
                    st.session_state['interview_resumed'] = True
                else:
                    st.session_state['selected_page'] = 'Genie'
                    st.session_state['interview_resumed'] = True
                st.rerun()

            st.divider()

        # Queue Status Widget - show if queue has items
        table_queue = state.get_table_queue()
        if table_queue:
            st.info(f"📋 Queue: {len(table_queue)} tables", icon=":material/list:")
            st.caption("Tables ready for documentation")

            if st.button("View Queue", use_container_width=True, key="sidebar_view_queue"):
                st.session_state['selected_page'] = 'Select'
                st.rerun()

            st.divider()

        # Save Progress button - always visible
        render_save_progress_button()

        st.divider()

        # History panel
        render_history_panel()

        st.divider()

        # Settings panel
        render_settings_panel()

        st.divider()

        # Context tips
        render_tips(workflow_step)


def render_page_content(page: str):
    """Render the content for the selected page."""
    state = get_state_manager()

    if page == "Select":
        render_table_browser()

    elif page == "Document":
        table_queue = state.get_table_queue()
        if table_queue:
            render_table_interview_unified()
        else:
            st.info("Add tables to queue first")
            st.caption("Go to the Select page to browse Unity Catalog and add tables to your queue.")

            with st.expander("How to get started", icon=":material/lightbulb:"):
                st.markdown("""
                1. Select a **Catalog** and **Schema** from the dropdowns
                2. Choose one or more tables from the list
                3. Optionally generate **data profiles** for better interviews
                4. Click **Start Documenting** to begin
                """)

    elif page == "Review":
        completed_tables = state.get_completed_tables()
        if completed_tables:
            render_review()
        else:
            st.info("No tables documented yet")
            st.caption("Complete the Document step to review your table comments here.")

    elif page == "Genie":
        # Always render Genie interview - it handles both cases (with/without tables)
        render_genie_interview_unified()

    elif page == "Export":
        completed_tables = state.get_completed_tables()
        if completed_tables:
            render_export()
        else:
            st.info("Nothing to export yet")
            st.caption("Complete documenting tables to export your YAML files.")

    elif page == "Editor":
        render_yaml_editor_page()

    elif page == "Library":
        render_library_panel()

    elif page == "Help":
        render_help_page()


def render_tips(workflow_step: str):
    """Render context-aware tips based on workflow step."""
    tips = {
        'browse': """
**Tips:**
- Generate data profiles for better interviews
- Add multiple related tables to queue
- Start with fact + dimension tables
        """,
        'table_interview': """
**Tips:**
- Keep answers concise and specific
- Use suggested inline options
- Generate YAML early if needed
        """,
        'review': """
**Tips:**
- Check all table comments carefully
- Edit any table if needed
- Configure Genie for multi-table queries
        """,
        'genie_interview': """
**Tips:**
- Focus on query patterns, not tech details
- Describe relationships between tables
- Provide example natural language queries
        """,
        'export': """
**Ready to export**
- Download individual YAMLs
- Get bulk ZIP with all files
- Follow usage instructions
        """
    }

    tip = tips.get(workflow_step)
    if tip:
        if workflow_step == 'export':
            st.success(tip, icon=":material/check_circle:")
        else:
            st.info(tip, icon=":material/lightbulb:")


def main():
    """Main app logic."""
    # Initialize
    initialize_session_state()
    state = get_state_manager()
    workflow_step = state.get_workflow_step()

    # Edit workflows are now handled through the unified Editor page

    # Define navigation pages with Material icons
    page_icons = {
        "Select": ":material/folder_open:",
        "Document": ":material/edit_note:",
        "Review": ":material/rate_review:",
        "Genie": ":material/auto_awesome:",
        "Export": ":material/download:",
        "Editor": ":material/edit_document:",  # YAML Editor
        "Library": ":material/library_books:",
        "Help": ":material/help:"  # Help & How To
    }
    pages = list(page_icons.keys())

    # Map workflow to page for default selection
    workflow_to_page = {
        'browse': 'Select',
        'table_interview': 'Document',
        'review': 'Review',
        'genie_interview': 'Genie',
        'export': 'Export',
        'library': 'Library',
        'help': 'Help'
    }

    # Initialize selected page in session state if not set
    if 'selected_page' not in st.session_state:
        st.session_state.selected_page = workflow_to_page.get(workflow_step, 'Select')

    # Render pills navigation
    st.markdown('<div class="pills-nav-container">', unsafe_allow_html=True)
    cols = st.columns(len(pages))

    for idx, (col, page_name) in enumerate(zip(cols, pages)):
        with col:
            icon = page_icons[page_name]
            is_active = st.session_state.selected_page == page_name

            # Use custom button styling based on active state
            button_type = "primary" if is_active else "secondary"

            if st.button(
                f"{icon} {page_name}",
                key=f"nav_pill_{page_name}",
                use_container_width=True,
                type=button_type,
                disabled=is_active
            ):
                st.session_state.selected_page = page_name
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="nav-spacer"></div>', unsafe_allow_html=True)

    # Render sidebar with history and settings
    render_sidebar()

    # Render content for the selected page
    render_page_content(st.session_state.selected_page)


if __name__ == "__main__":
    main()
