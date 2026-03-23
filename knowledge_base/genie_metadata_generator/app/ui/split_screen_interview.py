"""
Split-Screen Interview UI Component
Reusable component for section-based interviews with live YAML preview.
Material Design styling with flat icons.
"""

import logging

import streamlit as st
from llm.client import LLMRateLimitError, LLMTimeoutError
from llm.section_interview import SectionBasedInterview
from state import TableIdentifier, get_state_manager
from state.services import get_interview_service
from ui.constants import (
    BUTTON_ADD_MORE_TABLES,
    BUTTON_BACK_TO_REVIEW,
    BUTTON_BACK_TO_SELECT,
    BUTTON_COMPLETE_SECTION,
    BUTTON_CONTINUE,
    BUTTON_CONTINUE_INTERVIEW,
    BUTTON_GENERATE_YAML,
    BUTTON_SAVE_PROGRESS,
    BUTTON_SKIP_SECTION,
    BUTTON_START_FRESH,
    ICON_BACK,
    ICON_FORWARD,
)
from ui.content.help_content import INTERVIEW_TIPS
from ui.utils.formatting import format_table_count
from utils.data_conversion import library_yaml_to_table_data

logger = logging.getLogger(__name__)

# Pane height calculation - fits viewport with header/footer space
PANE_HEIGHT = 500  # Fixed height for scrollable panes


# ============================================================================
# ERROR HANDLING HELPERS
# ============================================================================

def _handle_interview_error(error: Exception, error_type: str, interview, interview_type: str, interview_service):
    """
    Handle interview errors with appropriate user feedback and logging.

    Args:
        error: The exception that occurred
        error_type: Type of error ('rate_limit', 'timeout', 'generic')
        interview: The interview instance
        interview_type: Type of interview ('table' or 'genie')
        interview_service: Interview service instance
    """
    if error_type == 'rate_limit':
        st.error(
            "⏱️ Rate limit reached. The LLM service is temporarily unavailable. "
            "Please wait a moment and try again.",
            icon=":material/error:"
        )
        with st.expander("What can I do?"):
            st.markdown("""
            - Wait 30-60 seconds before continuing
            - Your progress is auto-saved
            - The issue will resolve automatically
            """)
    elif error_type == 'timeout':
        st.error(
            "⏱️ Request timed out. The LLM service took too long to respond.",
            icon=":material/error:"
        )
        with st.expander("What can I do?"):
            st.markdown("""
            - Try again - timeouts are usually temporary
            - Your progress is auto-saved
            - Consider simplifying complex questions
            """)
    else:
        st.error(f"An error occurred: {str(error)}", icon=":material/error:")
        with st.expander("Error details"):
            st.code(str(error))

    # Try to save progress despite error
    try:
        if interview:
            interview_service.save_progress_async(interview, interview_type)
            st.info("✓ Your progress has been saved", icon=":material/save:")
    except Exception as save_error:
        logger.error(f"Failed to save progress after error: {save_error}", exc_info=True)


# ============================================================================
# ATOMIC INTERVIEW FUNCTIONS - Reusable across workflows
# ============================================================================

def start_table_interview(table_data: dict, interview_type: str = 'new'):
    """
    Atomic function to start a table interview using InterviewService.

    Can be called from multiple entry points:
    - Browse tables workflow
    - Library re-interview
    - Edit/regenerate existing table

    Args:
        table_data: Dict with catalog, schema, table, metadata
        interview_type: 'new' | 'reinterview' | 'edit'

    Returns:
        SectionBasedInterview instance or None on failure
    """
    state = get_state_manager()
    interview_service = get_interview_service(state)

    try:
        # Start interview with planning step using st.status for better feedback
        with st.status("Preparing interview...", expanded=True) as status:
            status.update(label="Analyzing table structure...")

            # Get connection for auto-profiling
            connection = state.get_connection()

            # Use service to start interview (will auto-generate profile if needed)
            interview = interview_service.start_table_interview(
                table_data,
                interview_type,
                connection=connection
            )

            if interview:
                # Log planning results
                planning = interview.get_planning_summary()
                if planning:
                    status.update(label=f"Ready! {planning['pre_populated_count']} fields pre-filled", state="complete")
                else:
                    status.update(label="Interview ready!", state="complete")
            else:
                status.update(label="Failed to start interview", state="error")

        return interview

    except Exception as e:
        logger.error(f"Failed to start table interview: {e}", exc_info=True)
        st.error(f"Failed to start interview: {str(e)}")
        import traceback
        with st.expander("Error details"):
            st.code(traceback.format_exc())
        return None


def start_genie_interview(completed_tables: list, source: str = 'current'):
    """
    Atomic function to start a Genie interview using InterviewService.

    Can be called from multiple entry points:
    - Current session completed tables
    - Library selection
    - Restore from history

    Args:
        completed_tables: List of completed table data dicts
        source: 'current' | 'library' | 'restored'

    Returns:
        SectionBasedInterview instance or None on failure
    """
    if not completed_tables:
        st.warning("No completed tables provided for Genie interview")
        return None

    state = get_state_manager()
    interview_service = get_interview_service(state)

    try:
        # Start interview with all completed tables using st.status for better feedback
        with st.status("Preparing Genie configuration...", expanded=True) as status:
            status.update(label=f"Analyzing {len(completed_tables)} tables...")

            # Get connection for auto-profiling
            connection = state.get_connection()

            # Use service to start interview (will auto-generate profiles if needed)
            interview = interview_service.start_genie_interview(
                completed_tables,
                source,
                connection=connection
            )

            if interview:
                # Log planning results
                planning = interview.get_planning_summary()
                if planning:
                    status.update(label=f"Ready! {planning['pre_populated_count']} fields pre-filled", state="complete")
                else:
                    status.update(label="Genie interview ready!", state="complete")
            else:
                status.update(label="Failed to start interview", state="error")

        return interview

    except Exception as e:
        logger.error(f"Failed to start Genie interview: {e}", exc_info=True)
        st.error(f"Failed to start Genie interview: {str(e)}")
        import traceback
        with st.expander("Error details"):
            st.code(traceback.format_exc())
        return None


# Removed _convert_library_yaml_to_table_data - now using utils.data_conversion.library_yaml_to_table_data


@st.dialog("Select Tables from Library", icon=":material/library_books:")
def _show_library_selection_dialog():
    """Dialog for selecting multiple table YAMLs from library to build Genie space."""
    from config import config
    from state import get_state_manager
    from state.services import get_library_service

    state = get_state_manager()

    # Check if Lakebase is enabled
    if not config.lakebase_enabled:
        st.warning("Library requires Lakebase to be enabled", icon=":material/warning:")
        return

    # Use LibraryService instead of direct persistence access
    library_service = get_library_service(state.user_email)
    if not library_service.is_available():
        st.warning("Lakebase connection not available", icon=":material/warning:")
        return

    st.markdown("Select table YAMLs to include in your Genie space:")

    # Get table YAMLs from library using service
    table_yamls = library_service.get_yamls(yaml_type='table_comment', limit=100)

    if not table_yamls:
        st.info("No table YAMLs in library yet", icon=":material/info:")
        st.caption("Complete table interviews to add YAMLs to library")
        return

    # Search filter
    search = st.text_input(
        "🔍 Search tables",
        placeholder="Filter by name...",
        key="library_search"
    )

    # Filter tables based on search
    filtered_yamls = table_yamls
    if search:
        search_lower = search.lower()
        filtered_yamls = [
            y for y in table_yamls
            if search_lower in y['table_name'].lower() or
               search_lower in y['catalog'].lower() or
               search_lower in y['schema'].lower()
        ]

    st.caption(f"Showing {len(filtered_yamls)} of {len(table_yamls)} tables")

    st.divider()

    # Multi-select checkboxes with preview
    selected_ids = []
    for yaml_item in filtered_yamls:
        full_name = f"{yaml_item['catalog']}.{yaml_item['schema']}.{yaml_item['table_name']}"

        with st.expander(f"📄 {full_name}", expanded=False):
            # Metadata row
            col_meta1, col_meta2 = st.columns(2)
            with col_meta1:
                st.caption(f"Catalog: {yaml_item['catalog']}")
                st.caption(f"Schema: {yaml_item['schema']}")
            with col_meta2:
                saved_date = yaml_item['updated_at'][:10] if yaml_item['updated_at'] else 'Unknown'
                st.caption(f"Saved: {saved_date}")

            # YAML preview
            yaml_preview = yaml_item['yaml_content'][:300]
            if len(yaml_item['yaml_content']) > 300:
                yaml_preview += "\n..."
            st.code(yaml_preview, language="yaml")

            # Select checkbox
            if st.checkbox(
                "Select this table",
                key=f"select_lib_{yaml_item['id']}",
                value=False
            ):
                selected_ids.append(yaml_item['id'])

    st.divider()

    st.caption(f"{format_table_count(len(selected_ids))} selected")

    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel", type="secondary", use_container_width=True):
            st.rerun()
    with col2:
        if st.button(
            "Create Genie Space",
            type="primary",
            use_container_width=True,
            icon=":material/auto_awesome:",
            disabled=len(selected_ids) == 0
        ):
            # Convert selected YAMLs to completed_tables format
            selected_yamls = [y for y in table_yamls if y['id'] in selected_ids]
            completed_tables = [library_yaml_to_table_data(y) for y in selected_yamls]

            # Set up state using StateManager methods instead of direct backend access
            for table in completed_tables:
                state.add_completed_table(table)
            state.clear_genie_interview()  # Clear any existing interview

            # Start Genie interview with selected tables
            st.toast(f"Starting Genie space with {len(completed_tables)} tables", icon=":material/check_circle:")
            st.rerun()


def ensure_table_profile(table_data: dict, connection) -> tuple:
    """
    Ensure table profile exists using ProfileService.

    Checks session state cache first. If not found, shows a "Generate Profile"
    button that generates the profile when clicked.

    Args:
        table_data: Dict with catalog, schema, table, metadata
        connection: Databricks SQL connection

    Returns:
        (has_profile: bool, profile_data: Optional[dict])
    """
    from state import get_state_manager
    from state.services import get_profile_service

    state = get_state_manager()
    profile_service = get_profile_service(state)

    catalog = table_data['catalog']
    schema = table_data['schema']
    table = table_data['table']

    # Check if profile exists
    if profile_service.has_profile(catalog, schema, table, table_data):
        profile_data = profile_service.get_profile(catalog, schema, table, table_data)
        return (True, profile_data)

    # Profile not found - show generate button
    st.info("📊 Data profile not generated for this table. Profiles improve interview quality.",
            icon=":material/lightbulb:")

    table_id_key = f"{catalog}.{schema}.{table}".replace('.', '_')
    if st.button("Generate Profile", type="primary", icon=":material/analytics:",
                 key=f"gen_profile_{table_id_key}"):
        try:
            with st.spinner(f"Profiling {table}..."):
                columns = table_data.get('metadata', {}).get('columns', [])

                success, profile_data, error = profile_service.generate_profile(
                    connection, catalog, schema, table, columns, table_data
                )

                if success:
                    st.success("Profile generated!", icon=":material/check_circle:")
                    # Display warnings if any
                    if profile_data and profile_data.get('profile', {}).get('table_stats', {}).get('errors'):
                        for err in profile_data['profile']['table_stats']['errors']:
                            st.warning(err, icon=":material/warning:")
                    st.rerun()
                else:
                    st.error(error, icon=":material/error:")
        except Exception as e:
            st.error(f"Profiling failed: {str(e)}")
            logger.error(f"Profile generation error: {e}", exc_info=True)


@st.dialog("Re-Profile Tables", icon=":material/refresh:")
def _show_reprofile_dialog(state, completed_tables):
    """Show dialog to re-profile completed tables before Genie interview."""
    from state.services import get_profile_service

    st.markdown("**Refresh table profiles with latest data statistics**")
    st.caption(f"You have {len(completed_tables)} documented table(s)")

    st.divider()

    # Show table list with profile status
    st.markdown("**Tables to re-profile:**")

    tables_to_profile = []
    for table_data in completed_tables:
        table_id = TableIdentifier(
            catalog=table_data['catalog'],
            schema=table_data['schema'],
            table=table_data['table']
        )

        col_name, col_status = st.columns([3, 1])
        with col_name:
            st.caption(f"📊 {table_data['catalog']}.{table_data['schema']}.{table_data['table']}")
        with col_status:
            if state.has_profile(table_id):
                st.caption("✓ Has profile")
            else:
                st.caption("⚠️ No profile")

        tables_to_profile.append((table_id, table_data))

    st.divider()

    # Action buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", type="secondary", use_container_width=True):
            st.session_state['show_reprofile_dialog'] = False
            st.rerun()

    with col2:
        if st.button("Re-Profile All", type="primary", use_container_width=True, icon=":material/refresh:"):
            # Close dialog
            st.session_state['show_reprofile_dialog'] = False

            # Get connection
            connection = state.get_connection()
            if not connection:
                st.error("Database connection not available")
                return

            # Initialize profile service
            profile_service = get_profile_service(state)

            # Batch re-profile
            with st.status(f"Re-profiling {len(tables_to_profile)} tables...", expanded=True) as status:
                success_count = 0
                for idx, (table_id, table_data) in enumerate(tables_to_profile):
                    status.update(
                        label=f"Profiling {idx+1}/{len(tables_to_profile)}: {table_id.table}"
                    )

                    try:
                        # Get columns from table metadata
                        columns = table_data.get('metadata', {}).get('columns', [])

                        # Generate fresh profile
                        success, profile_data, error = profile_service.generate_profile(
                            connection,
                            table_id.catalog,
                            table_id.schema,
                            table_id.table,
                            columns,
                            table_data
                        )

                        if success:
                            # Update completed_tables with new profile_summary
                            # The profile_service already updated table_data['metadata']['profile_summary']
                            # Now we need to persist it back to completed_tables
                            state.add_completed_table(table_data)
                            success_count += 1
                            status.update(label=f"✓ Profiled: {table_id.table}")
                        else:
                            status.update(label=f"⚠️ Skipped: {table_id.table} - {error}")

                    except Exception as e:
                        logger.error(f"Failed to profile {table_id.table}: {e}")
                        status.update(label=f"❌ Failed: {table_id.table}")

                status.update(
                    label=f"Re-profiling complete: {success_count}/{len(tables_to_profile)} successful",
                    state="complete"
                )

            st.success(f"✓ Re-profiled {success_count} table(s)")
            st.rerun()


def _render_resume_card(interview: SectionBasedInterview, interview_type: str):
    """Render Material Design resume card when session is restored."""
    st.info(
        "**Resuming Interview**",
        icon=":material/history:"
    )

    with st.container():
        # Get interview progress
        current_section = interview.current_section_idx
        total_sections = len(interview.sections)

        # Count questions answered (approximate based on conversation history)
        questions_answered = len([m for m in interview.conversation_history if m['role'] == 'user']) - 1  # Subtract resume message

        # Get current section name
        section_name = interview.sections[current_section]['name'] if current_section < total_sections else "Complete"

        # Show table name if available
        if interview_type == 'table' and interview.context_data:
            table_name = interview.context_data.get('table', 'Unknown')
            st.markdown(f"**Table:** {table_name}")
        elif interview_type == 'genie':
            st.markdown("**Genie Space Configuration**")

        # Progress metrics (Material design)
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Section",
                f"{current_section + 1} of {total_sections}",
                help="Current section"
            )
        with col2:
            progress_pct = int((current_section / total_sections) * 100) if total_sections > 0 else 0
            st.metric(
                "Progress",
                f"{progress_pct}%",
                help="Interview completion"
            )

        st.caption(f"**Current Section:** {section_name}")
        st.caption(f"**Questions Answered:** {questions_answered}")

        st.divider()

        # Continue button is not needed as interview will continue automatically
        st.success("Interview will continue below", icon=":material/play_arrow:")


def _handle_section_action(action: str, interview, interview_type: str, on_complete_callback):
    """
    Batch state updates for section actions using InterviewService.

    Handles skip, complete, and generate actions atomically with proper state persistence.

    Args:
        action: Action type - "skip", "complete", or "generate"
        interview: SectionBasedInterview instance
        interview_type: 'table' or 'genie'
        on_complete_callback: Optional callback when interview completes
    """
    import streamlit as st

    state = get_state_manager()
    interview_service = get_interview_service(state)

    try:
        if action == "skip":
            interview_service.skip_section(interview, interview_type)
            if interview.is_complete() and on_complete_callback:
                on_complete_callback()

        elif action == "complete":
            interview_service.complete_section(interview, interview_type)
            if interview.is_complete() and on_complete_callback:
                on_complete_callback()

        elif action == "generate":
            if interview.is_complete() and on_complete_callback:
                on_complete_callback()

        st.rerun()

    except Exception as e:
        logger.error(f"Section action failed: {e}", exc_info=True)
        st.error(f"Failed to {action} section: {str(e)}")
        st.rerun()


def render_split_screen_interview(
    interview: SectionBasedInterview,
    yaml_state_key: str,
    title: str,
    description: str,
    interview_type: str,
    on_complete_callback=None
):
    """
    Generic split-screen interview UI using InterviewService.

    Args:
        interview: SectionBasedInterview instance
        yaml_state_key: Session state key for storing YAML
        title: Interview title
        description: Interview description
        interview_type: 'table' or 'genie'
        on_complete_callback: Optional function to call when interview complete
    """
    state = get_state_manager()
    interview_service = get_interview_service(state)

    # Header section - Material typography
    st.markdown(f"#### {title}")
    st.caption(description)

    # Show planning summary if available - compact inline format
    planning_summary = interview.get_planning_summary()
    if planning_summary:
        st.caption(f"📋 Pre-filled: {planning_summary['pre_populated_count']} | Questions: {planning_summary['questions_count']} | Est. Time: {planning_summary['estimated_time']}")

    # Two-column layout
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown("**Interview Progress**")

        # Progress metrics
        current = interview.current_section_idx
        total = len(interview.sections)
        questions_answered = len(interview.conversation_history) // 2
        progress = current / total if total > 0 else 0
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Section", f"{current + 1} of {total}")
        with col2:
            st.metric("Questions", questions_answered)
        with col3:
            remaining = total - (current + 1)
            est_time = remaining * 2  # ~2 min per section
            st.metric("Est. Time", f"~{est_time} min" if remaining > 0 else "Almost done!")

        # Visual progress bar with current section
        if current < total:
            section_name = interview.sections[current]['name']
            st.progress(progress, text=f"Current: {section_name}")
        else:
            st.progress(1.0, text="All sections complete!")

        # Section badges
        st.markdown("**Sections:**")
        cols = st.columns(min(total, 4))  # Max 4 columns for readability
        for idx, section in enumerate(interview.sections):
            col_idx = idx % len(cols)
            with cols[col_idx]:
                section_short = section['name'][:10]
                if idx < current:
                    st.success(f"✓ {section_short}")
                elif idx == current:
                    st.info(f"→ {section_short}")
                else:
                    st.caption(f"○ {section_short}")

        st.divider()

        # Show last saved indicator
        if len(interview.conversation_history) > 0:
            last_save_count = (len(interview.conversation_history) // 6) * 6
            if last_save_count > 0:
                st.caption(f"💾 Last auto-saved at question {last_save_count // 2}")

        if current < total:
            section_name = interview.sections[current]['name']
            section_optional = interview.sections[current].get('optional', False)

            if section_optional:
                st.info(f"Section {current + 1}/{total}: {section_name} (Optional)", icon=":material/help:")
            else:
                st.info(f"Section {current + 1}/{total}: {section_name}", icon=":material/edit_note:")
        else:
            st.success("All sections complete!", icon=":material/check_circle:")

        # Chat history in scrollable container
        messages = interview.conversation_history[1:]  # Skip system prompt

        # Find the last assistant message index
        last_assistant_idx = -1
        for i in range(len(messages) - 1, -1, -1):
            if messages[i]['role'] == 'assistant':
                last_assistant_idx = i
                break

        # Scrollable chat container - fixed height with internal scroll
        chat_container = st.container(height=PANE_HEIGHT)

        with chat_container:
            if len(messages) > 1 and last_assistant_idx > 0:
                # Collapse all prior messages (everything before the last assistant message)
                earlier_messages = messages[:last_assistant_idx]

                # Show collapsed earlier messages
                with st.expander(f"Previous conversation ({len(earlier_messages)} messages)", expanded=False, icon=":material/history:"):
                    for msg in earlier_messages:
                        if msg['role'] == 'assistant':
                            with st.chat_message("assistant", avatar=":material/smart_toy:"):
                                # Truncate long messages in collapsed view
                                content = msg['content']
                                if len(content) > 500:
                                    st.markdown(content[:500] + "...")
                                else:
                                    st.markdown(content)
                        else:
                            with st.chat_message("user", avatar=":material/person:"):
                                st.markdown(msg['content'])

                # Show only the most recent assistant message expanded
                if last_assistant_idx >= 0:
                    msg = messages[last_assistant_idx]
                    with st.chat_message("assistant", avatar=":material/smart_toy:"):
                        st.markdown(msg['content'])

                    # Show any user messages after the last assistant message
                    for msg in messages[last_assistant_idx + 1:]:
                        if msg['role'] == 'user':
                            with st.chat_message("user", avatar=":material/person:"):
                                st.markdown(msg['content'])
            else:
                # Show all messages if only 1 or no prior messages to collapse
                for msg in messages:
                    if msg['role'] == 'assistant':
                        with st.chat_message("assistant", avatar=":material/smart_toy:"):
                            st.markdown(msg['content'])
                    else:
                        with st.chat_message("user", avatar=":material/person:"):
                            st.markdown(msg['content'])

        # User input
        if current < total:
            user_input = st.chat_input("Your answer...", key=f"{yaml_state_key}_input")

            if user_input:
                try:
                    # Use service to answer question with auto-save
                    interview_service.answer_question(interview, user_input, interview_type)
                    # Auto-save notification
                    if len(interview.conversation_history) % 6 == 0:
                        st.success("✓ Progress auto-saved", icon="💾")

                    st.rerun()
                except LLMRateLimitError as e:
                    logger.error(f"Rate limit error: {e}")
                    _handle_interview_error(e, 'rate_limit', interview, interview_type, interview_service)
                except LLMTimeoutError as e:
                    logger.error(f"Timeout error: {e}")
                    _handle_interview_error(e, 'timeout', interview, interview_type, interview_service)
                except Exception as e:
                    logger.error(f"Interview error: {e}", exc_info=True)
                    _handle_interview_error(e, 'generic', interview, interview_type, interview_service)

            # Action buttons
            st.divider()
            col_save, col_skip, col_complete = st.columns(3)

            with col_save:
                if st.button(BUTTON_SAVE_PROGRESS, use_container_width=True, key=f"{yaml_state_key}_save_btn"):
                    try:
                        interview_service.save_interview_progress(interview, interview_type)
                        st.toast("✓ Progress saved!", icon="💾")
                    except Exception as e:
                        logger.error(f"Failed to save progress: {e}")
                        st.toast("⚠️ Save failed", icon=":material/error:")
                    # No rerun needed - toast is non-blocking

            with col_skip:
                if st.button(BUTTON_SKIP_SECTION, key=f"{yaml_state_key}_skip", icon=":material/skip_next:", use_container_width=True):
                    _handle_section_action("skip", interview, interview_type, on_complete_callback)

            with col_complete:
                if st.button(BUTTON_COMPLETE_SECTION, key=f"{yaml_state_key}_complete", icon=":material/check:", use_container_width=True):
                    _handle_section_action("complete", interview, interview_type, on_complete_callback)

            st.divider()

            # Final actions
            col_gen = st.columns(1)[0]
            with col_gen:
                if st.button(BUTTON_GENERATE_YAML, key=f"{yaml_state_key}_generate", type="primary", icon=":material/code:", use_container_width=True):
                    _handle_section_action("generate", interview, interview_type, on_complete_callback)
        else:
            # Interview complete - show final actions
            st.divider()

            col_d, col_e = st.columns(2)

            with col_d:
                workflow_step = state.get_workflow_step()
                back_label = BUTTON_BACK_TO_SELECT if workflow_step == 'table_interview' else BUTTON_BACK_TO_REVIEW
                if st.button(back_label, key=f"{yaml_state_key}_back", icon=ICON_BACK):
                    if workflow_step == 'table_interview':
                        state.set_workflow_step('browse')
                        st.session_state['selected_page'] = 'Select'
                    elif workflow_step == 'genie_interview':
                        state.set_workflow_step('review')
                        st.session_state['selected_page'] = 'Review'
                    st.rerun()

            with col_e:
                if st.button(BUTTON_CONTINUE, type="primary", key=f"{yaml_state_key}_continue", icon=ICON_FORWARD):
                    if on_complete_callback:
                        on_complete_callback()
                    st.rerun()

    with col_right:
        st.markdown("**Generated YAML**")

        # Horizontal section indicators at top
        section_cols = st.columns(len(interview.sections))
        for idx, (col, section) in enumerate(zip(section_cols, interview.sections, strict=False)):
            with col:
                section_key = section['key']

                if section_key in interview.completed_sections:
                    if interview.completed_sections[section_key] is None:
                        # Skipped section
                        st.caption(f"⊘ {section['name']}")
                    else:
                        # Completed section
                        st.caption(f"✓ {section['name']}")
                elif idx == current:
                    # Current section - bold
                    st.markdown(f"**○ {section['name']}**")
                else:
                    # Pending section
                    st.caption(f"○ {section['name']}")

        st.divider()

        # Scrollable YAML container - matches interview pane height
        yaml_container = st.container(height=PANE_HEIGHT)

        with yaml_container:
            # Show merged YAML so far (includes pre-populated content)
            merged_yaml = None  # Initialize to prevent NameError if exception occurs
            try:
                # Cache YAML generation with section hash as key
                yaml_cache_key = f"{yaml_state_key}_yaml_cache"
                section_hash = hash(str(interview.completed_sections))

                if (yaml_cache_key not in st.session_state or
                    st.session_state.get(f"{yaml_cache_key}_hash") != section_hash):
                    # Use pre-populated YAML if no sections completed yet
                    if not any(v for k, v in interview.completed_sections.items() if k != 'skeleton' and v):
                        merged_yaml = interview.get_pre_populated_yaml()
                    else:
                        merged_yaml = interview.get_merged_yaml()

                    # Cache the result
                    st.session_state[yaml_cache_key] = merged_yaml
                    st.session_state[f"{yaml_cache_key}_hash"] = section_hash
                else:
                    # Use cached YAML
                    merged_yaml = st.session_state[yaml_cache_key]

                # Store in session state (for compatibility)
                st.session_state[yaml_state_key] = merged_yaml

                # Syntax highlighting
                st.code(merged_yaml, language="yaml", line_numbers=True)
            except Exception as e:
                st.error(f"Error generating YAML: {str(e)}")
                logger.error(f"YAML generation error: {e}", exc_info=True)
                # Ensure merged_yaml has a fallback value
                if merged_yaml is None:
                    merged_yaml = "# Error: Failed to generate YAML\n# Please contact support if this persists"
                    st.session_state[yaml_state_key] = merged_yaml

        # Download button when complete (with validation)
        if current >= total and merged_yaml and merged_yaml.strip() and not merged_yaml.startswith("# Error:"):
            st.divider()

            filename = f"{interview.template_type}_{yaml_state_key}.yml"

            st.download_button(
                "Download YAML",
                merged_yaml,
                file_name=filename,
                mime="text/yaml",
                key=f"{yaml_state_key}_download",
                icon=":material/download:"
            )


def render_table_interview_unified():
    """Render table comment interview using split-screen UI."""

    state = get_state_manager()

    # Initialize interview if not started
    interview = state.get_table_interview()

    # Check if session was just restored from history - show resume card and add resume context once
    if interview is not None and st.session_state.get('_session_just_restored'):
        # Show Material Design resume card
        _render_resume_card(interview, 'table')

        # Add resume context to conversation
        interview.conversation_history.append({
            "role": "user",
            "content": "[Session resumed - please continue from where we left off]"
        })
        state.set_table_interview(interview)  # Persist the resume message
        del st.session_state._session_just_restored  # Clear flag so it only happens once
        logger.info("Added resume context for restored table interview session")

    # Check for auto-saved interview to resume
    if interview is not None and 'interview_resumed' not in st.session_state and not st.session_state.get('_session_just_restored'):
        st.info("📋 You have an interview in progress", icon=":material/history:")

        # Show progress stats
        current = interview.current_section_idx + 1
        total = len(interview.sections)
        questions_answered = len(interview.conversation_history) // 2
        progress_pct = int((current / total) * 100)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Section", f"{current} of {total}")
        with col2:
            st.metric("Questions", questions_answered)
        with col3:
            st.metric("Progress", f"{progress_pct}%")

        st.divider()

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(BUTTON_CONTINUE_INTERVIEW, type="primary", use_container_width=True, key="resume_table_interview"):
                st.session_state['interview_resumed'] = True
                st.session_state['interview'] = interview
                st.rerun()

        with col_b:
            if st.button(BUTTON_START_FRESH, use_container_width=True, key="start_fresh_table"):
                state.clear_table_interview()
                st.rerun()

        st.stop()  # Don't render interview until user chooses

    if interview is None:
        # Get current table data
        table_queue = state.get_table_queue()
        current_idx = state.get_current_table_index()

        if not table_queue:
            completed = state.get_completed_tables()

            if completed:
                st.success(f"✓ Completed {format_table_count(len(completed))} so far!", icon=":material/check_circle:")
                st.info("Your queue is empty. Add more tables to continue documenting.", icon=":material/info:")
            else:
                st.warning("No tables in queue", icon=":material/warning:")
                st.caption("Add tables to your queue to start documenting.")

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                if st.button(BUTTON_ADD_MORE_TABLES, type="primary", use_container_width=True, icon=":material/add:"):
                    state.set_workflow_step('browse')
                    st.session_state['selected_page'] = 'Select'
                    st.rerun()

            with col2:
                if completed:
                    if st.button("Review Completed", use_container_width=True, icon=":material/visibility:"):
                        state.set_workflow_step('review')
                        st.session_state['selected_page'] = 'Review'
                        st.rerun()
                else:
                    if st.button(BUTTON_BACK_TO_SELECT, use_container_width=True, icon=":material/home:"):
                        state.set_workflow_step('browse')
                        st.session_state['selected_page'] = 'Select'
                        st.rerun()
            return

        # Validate current index is within bounds
        if current_idx < 0 or current_idx >= len(table_queue):
            logger.warning(f"Current index {current_idx} out of bounds for queue length {len(table_queue)}, resetting to 0")
            current_idx = 0
            state.set_current_table_index(0)

        table_data = table_queue[current_idx]

        # Use atomic interview start function
        interview = start_table_interview(table_data, interview_type='new')

        if interview is None:
            # Error already displayed by start_table_interview
            if st.button(BUTTON_BACK_TO_SELECT, use_container_width=True, icon=ICON_BACK):
                state.set_workflow_step('browse')
                st.session_state['selected_page'] = 'Select'
                st.rerun()
            return

        state.set_table_interview(interview)

    # Get current table info
    table_queue = state.get_table_queue()
    current_idx = state.get_current_table_index()

    # Validate current index is within bounds
    if not table_queue or current_idx < 0 or current_idx >= len(table_queue):
        st.error("Table queue is empty or current index is invalid")
        if st.button(BUTTON_BACK_TO_SELECT, use_container_width=True, icon=ICON_BACK):
            state.set_workflow_step('browse')
            st.session_state['selected_page'] = 'Select'
            st.rerun()
        return

    table_data = table_queue[current_idx]
    table_name = f"{table_data['catalog']}.{table_data['schema']}.{table_data['table']}"

    def on_complete():
        """Handle completion of table interview using InterviewService."""
        interview_service = get_interview_service(state)

        # Finalize interview - saves YAML and updates state atomically
        success = interview_service.finalize_table_interview(interview, table_data)

        if success:
            # Move to next table or review
            next_idx = current_idx + 1
            state.set_current_table_index(next_idx)

            if next_idx >= len(table_queue):
                # All done - go to review
                state.set_workflow_step('review')
                st.session_state['selected_page'] = 'Review'
            else:
                # Next table
                st.rerun()
        else:
            st.error("Failed to complete interview", icon=":material/error:")
            logger.error("Failed to finalize table interview")

    # First-time tips for table interviews
    if interview.current_section_idx == 0 and len(interview.conversation_history) <= 2:
        with st.expander("Interview Tips", icon=":material/help:", expanded=True):
            st.markdown(INTERVIEW_TIPS)

    render_split_screen_interview(
        interview,
        f"table_{current_idx}",
        f":material/edit_note: Table Comment Interview ({current_idx + 1}/{len(table_queue)})",
        f"Generating metadata for: **{table_name}**",
        'table',  # interview_type
        on_complete
    )


def render_genie_interview_unified():
    """Render Genie metadata interview using split-screen UI."""

    state = get_state_manager()

    # Get current state
    completed_tables = state.get_completed_tables()
    interview = state.get_genie_interview()

    # Check if session was just restored from history - show resume card and add resume context once
    if interview is not None and st.session_state.get('_session_just_restored'):
        # Show Material Design resume card
        _render_resume_card(interview, 'genie')

        # Add resume context to conversation
        interview.conversation_history.append({
            "role": "user",
            "content": "[Session resumed - please continue from where we left off]"
        })
        state.set_genie_interview(interview)  # Persist the resume message
        del st.session_state._session_just_restored  # Clear flag so it only happens once
        logger.info("Added resume context for restored genie interview session")

    # Check for auto-saved Genie interview to resume
    if interview is not None and 'interview_resumed' not in st.session_state and not st.session_state.get('_session_just_restored'):
        st.info("📋 You have a Genie interview in progress", icon=":material/auto_awesome:")

        # Show progress stats
        current = interview.current_section_idx + 1
        total = len(interview.sections)
        questions_answered = len(interview.conversation_history) // 2
        progress_pct = int((current / total) * 100)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Section", f"{current} of {total}")
        with col2:
            st.metric("Questions", questions_answered)
        with col3:
            st.metric("Progress", f"{progress_pct}%")

        st.divider()

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(BUTTON_CONTINUE_INTERVIEW, type="primary", use_container_width=True, key="resume_genie_interview"):
                st.session_state['interview_resumed'] = True
                st.session_state['interview'] = interview
                st.rerun()

        with col_b:
            if st.button(BUTTON_START_FRESH, use_container_width=True, key="start_fresh_genie"):
                state.clear_genie_interview()
                st.rerun()

        st.stop()  # Don't render interview until user chooses

    # If no interview started yet, show selection screen
    if interview is None:
        if not completed_tables:
            # No tables - offer library or start documentation
            st.info("Configure your Genie Space by documenting tables first or selecting from library", icon=":material/auto_awesome:")
            st.caption("You need documented tables to create a Genie Space.")

            st.divider()

            # Check library availability
            from state.services import get_library_service
            library_service = get_library_service(state.user_email)
            library_available = library_service.is_available()

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Document Tables", type="primary", use_container_width=True, icon=":material/edit_note:"):
                    state.set_workflow_step('browse')
                    st.session_state['selected_page'] = 'Select'
                    st.rerun()

            with col2:
                if library_available:
                    if st.button("Select from Library", use_container_width=True, icon=":material/library_books:"):
                        _show_library_selection_dialog()
                else:
                    st.button("Library Unavailable", disabled=True, use_container_width=True)
                    st.caption("Lakebase required")

            with col3:
                if st.button(BUTTON_BACK_TO_SELECT, use_container_width=True, icon=ICON_BACK):
                    state.set_workflow_step('browse')
                    st.session_state['selected_page'] = 'Select'
                    st.rerun()
            return
        else:
            # Have completed tables - offer choice
            st.info("**Ready to configure Genie Space**", icon=":material/auto_awesome:")
            st.caption(f"You have {len(completed_tables)} completed table(s) in this session")

            st.divider()

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button(BUTTON_BACK_TO_REVIEW, use_container_width=True, icon=ICON_BACK):
                    state.set_workflow_step('review')
                    st.session_state['selected_page'] = 'Review'
                    st.rerun()
            with col2:
                if st.button("Use Current Tables", use_container_width=True, icon=":material/table_chart:", type="primary"):
                    # Start interview with current tables
                    interview = start_genie_interview(completed_tables, source='current')
                    if interview:
                        state.set_genie_interview(interview)
                        st.rerun()
                    # Error already displayed by start_genie_interview if None
            with col3:
                if st.button("Select from Library", use_container_width=True, icon=":material/library_books:"):
                    _show_library_selection_dialog()
            return

    # Interview in progress - render it
    num_tables = len(completed_tables)

    def on_complete():
        """Handle completion of Genie interview using InterviewService."""
        interview_service = get_interview_service(state)

        # Finalize interview - saves YAML and clears state atomically
        success = interview_service.finalize_genie_interview(interview)

        if success:
            # Go to export
            state.set_workflow_step('export')
            st.session_state['selected_page'] = 'Export'
        else:
            st.error("Failed to complete Genie interview", icon=":material/error:")
            logger.error("Failed to finalize Genie interview")

    # First-time tips for Genie interviews
    if interview.current_section_idx == 0 and len(interview.conversation_history) <= 2:
        with st.expander("Configuring Your Genie Space", icon=":material/auto_awesome:", expanded=True):
            st.markdown("""
            **What Makes a Great Genie Space:**
            - **SQL Expressions** - Business metrics like "revenue", "active users"
            - **Query Instructions** - Default logic (e.g., "recent" = last 30 days)
            - **Example Queries** - Common patterns users will ask
            - **Clarification Rules** - How to handle ambiguous questions

            **AI Will Suggest:**
            - SQL expressions based on your table columns
            - Query patterns from table relationships
            - Example queries users might ask

            **Your Expertise Needed:**
            - Business-specific metrics and calculations
            - Team-specific default time ranges
            - Common questions your users ask

            **Result:** Better natural language queries, accurate results, faster responses
            """)

    render_split_screen_interview(
        interview,
        "genie_space",
        ":material/auto_awesome: Genie Space Configuration",
        f"Creating query-optimized metadata for **{num_tables} tables**",
        'genie',  # interview_type
        on_complete
    )
