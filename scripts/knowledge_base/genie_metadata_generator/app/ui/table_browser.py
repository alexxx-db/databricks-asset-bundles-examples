"""
Table browser UI component.
Browse Unity Catalog: catalog -> schema -> table
Material Design styling with flat icons.
"""

import streamlit as st
import logging
from state import get_state_manager, TableIdentifier
from state.services import get_catalog_service, get_profile_service
from ui.constants import (
    BUTTON_CLEAR_QUEUE,
    BUTTON_GENERATE_PROFILE,
    BUTTON_START_INTERVIEW,
    BUTTON_START_DOCUMENTING,
    ICON_DELETE,
    ICON_ANALYTICS,
    ICON_FORWARD
)
from ui.utils.formatting import format_table_count, format_time_estimate
from ui.content.help_content import GETTING_STARTED_GUIDE

logger = logging.getLogger(__name__)


def _render_workflow_diagram():
    """Render the visual workflow diagram using native Streamlit with Material icons."""
    st.markdown("**How It Works**")

    # Workflow steps using columns
    col1, col2, col3, col4 = st.columns(4)

    steps = [
        (col1, ":material/folder_open:", "Select", "Pick tables from catalog"),
        (col2, ":material/bar_chart:", "Profile", "AI analyzes your data"),
        (col3, ":material/auto_awesome:", "Generate", "LLM fills templates"),
        (col4, ":material/download:", "Export", "Download YAML files")
    ]

    for col, icon, title, desc in steps:
        with col:
            st.markdown(f"{icon} **{title}**")
            st.caption(desc)


def _get_unprofiled_tables(state, queue):
    """
    Get list of unprofiled tables from queue.

    Args:
        state: StateManager instance
        queue: List of table data dicts

    Returns:
        List of table data dicts that don't have profiles
    """
    return [
        t for t in queue
        if not state.has_profile(TableIdentifier(t['catalog'], t['schema'], t['table']))
    ]


def _check_tables_in_queue(state, catalog, schema, table_names):
    """
    Check which selected tables are already in queue.

    Args:
        state: StateManager instance
        catalog: Catalog name
        schema: Schema name
        table_names: List of table names to check

    Returns:
        Tuple of (in_queue, not_in_queue) where each is a list of table names
    """
    queue = state.get_table_queue()
    queue_keys = {f"{t['catalog']}_{t['schema']}_{t['table']}" for t in queue}

    in_queue = []
    not_in_queue = []

    for table_name in table_names:
        table_key = f"{catalog}_{schema}_{table_name}"
        if table_key in queue_keys:
            in_queue.append(table_name)
        else:
            not_in_queue.append(table_name)

    return in_queue, not_in_queue


@st.dialog("Clear Queue?", icon=":material/warning:")
def _show_clear_queue_dialog(state):
    """Confirmation dialog for clearing queue."""
    queue = state.get_table_queue()
    queue_count = len(queue)

    st.warning(f"⚠️ This will remove {format_table_count(queue_count)} from your queue",
               icon=":material/warning:")
    st.caption("This action cannot be undone. Tables will need to be re-added.")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel", type="secondary", use_container_width=True, key="clear_queue_cancel"):
            st.rerun()
    with col2:
        if st.button(BUTTON_CLEAR_QUEUE, type="primary", use_container_width=True,
                     icon=ICON_DELETE, key="clear_queue_confirm"):
            state.clear_queue()
            st.toast("Queue cleared", icon=":material/check_circle:")
            st.rerun()


def _render_queue_section(state, catalog, schema, catalog_service, profile_service, connection):
    """Render inline queue management section."""
    queue = state.get_table_queue()

    if not queue:
        return

    st.divider()

    with st.expander(f"📋 Current Queue ({format_table_count(len(queue))})", expanded=True, icon=":material/list:"):
        # Queue list
        for idx, table_data in enumerate(queue):
            col_name, col_profile, col_remove = st.columns([5, 2, 1])

            with col_name:
                st.caption(f"{table_data['catalog']}.{table_data['schema']}.{table_data['table']}")

            with col_profile:
                table_id = TableIdentifier(
                    catalog=table_data['catalog'],
                    schema=table_data['schema'],
                    table=table_data['table']
                )
                if state.has_profile(table_id):
                    st.caption("✓ Profiled")
                else:
                    st.caption("No profile")

            with col_remove:
                if st.button("×", key=f"remove_queue_{idx}", help="Remove from queue"):
                    queue.pop(idx)
                    state.set_table_queue(queue)
                    st.rerun()

        st.divider()

        # Queue actions
        unprofiled = _get_unprofiled_tables(state, queue)

        col_clear, col_profile, col_start = st.columns(3)

        with col_clear:
            if st.button(BUTTON_CLEAR_QUEUE, use_container_width=True, icon=ICON_DELETE):
                _show_clear_queue_dialog(state)

        with col_profile:
            if unprofiled:
                if st.button(
                    f"Profile {len(unprofiled)}",
                    use_container_width=True,
                    type="secondary",
                    icon=":material/analytics:",
                    key="bulk_profile_queue"
                ):
                    st.session_state['trigger_bulk_profile'] = True
                    st.rerun()

        with col_start:
            # Validation before allowing start
            can_start = len(queue) > 0
            button_disabled = not can_start

            if st.button(
                BUTTON_START_DOCUMENTING,
                type="primary",
                use_container_width=True,
                icon=":material/play_arrow:",
                disabled=button_disabled
            ):
                # Final validation
                if not queue:
                    st.error("❌ No tables in queue. Please add tables first.")
                    return

                # Check profiling status
                unprofiled = _get_unprofiled_tables(state, queue)

                if unprofiled:
                    st.warning(f"⚠️ {len(unprofiled)}/{len(queue)} tables not profiled")
                    st.caption("Interviews will take longer without profiles (50-70% more questions)")

                # Time estimate
                has_profiles = len(unprofiled) == 0
                st.info(f"⏱️ Estimated time: {format_time_estimate(len(queue), has_profiles)} ({format_table_count(len(queue))})")

                # Proceed
                state.set_current_table_index(0)
                state.set_workflow_step('table_interview')
                st.session_state['selected_page'] = 'Document'
                st.rerun()


def render_table_browser():
    """Render the table browser interface."""
    state = get_state_manager()

    # Page header
    st.markdown("#### :material/folder_open: Browse Tables")
    st.caption("Generate standardized table comments and Genie metadata for Unity Catalog.")

    # Visual workflow diagram
    _render_workflow_diagram()

    # How to get started section
    with st.expander("How to get started", icon=":material/lightbulb:", expanded=False):
        st.markdown(GETTING_STARTED_GUIDE)

    st.divider()

    # Get or create connection
    connection = state.get_connection()
    if not connection:
        try:
            from auth.service_principal import get_connection
            connection = get_connection()
            state.set_connection(connection)
        except Exception as e:
            st.error(f"Failed to connect to Databricks: {str(e)}")
            st.info("Please ensure environment variables are set:\n- DATABRICKS_HOST\n- DATABRICKS_WAREHOUSE_ID\n- DATABRICKS_CLIENT_ID\n- DATABRICKS_CLIENT_SECRET")
            return

    # Initialize services
    conn_id = state.session_key
    catalog_service = get_catalog_service(connection, conn_id)
    profile_service = get_profile_service(state)

    # Handle bulk profile trigger (from queue actions)
    if st.session_state.get('trigger_bulk_profile'):
        st.session_state['trigger_bulk_profile'] = False

        queue = state.get_table_queue()

        # Get unprofiled tables from queue
        unprofiled_tables = []
        for table_data in queue:
            table_id = TableIdentifier(
                catalog=table_data['catalog'],
                schema=table_data['schema'],
                table=table_data['table']
            )
            if not state.has_profile(table_id):
                unprofiled_tables.append(table_data)

        if unprofiled_tables:
            with st.status(f"Profiling {len(unprofiled_tables)} tables...", expanded=True) as status:
                # Batch profile
                results = profile_service.generate_profiles_batch(connection, unprofiled_tables)

                success_count = sum(1 for s, _, _ in results.values() if s)

                if success_count == len(unprofiled_tables):
                    status.update(
                        label=f"Successfully profiled all {success_count} tables!",
                        state="complete"
                    )
                    st.success(f"✓ Profiled {success_count} tables - ready to document!", icon=":material/check_circle:")
                else:
                    failed_count = len(unprofiled_tables) - success_count
                    status.update(
                        label=f"Profiled {success_count}/{len(unprofiled_tables)} tables",
                        state="error"
                    )
                    st.warning(f"Profiled {success_count} tables. {failed_count} failed.", icon=":material/warning:")

    # Three-level hierarchical selector
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(":material/menu_book: **Catalog**")
        try:
            catalogs = catalog_service.get_catalogs()
            catalog_names = [c[0] for c in catalogs]

            if not catalog_names:
                st.warning("No catalogs found")
                return

            catalog = st.selectbox(
                "Select catalog",
                catalog_names,
                key="selected_catalog",
                label_visibility="collapsed"
            )
        except Exception as e:
            st.error(f"Error loading catalogs: {str(e)}")
            return

    with col2:
        st.markdown(":material/storage: **Schema**")
        if catalog:
            try:
                schemas = catalog_service.get_schemas(catalog)
                schema_names = [s[0] for s in schemas]

                if not schema_names:
                    st.warning(f"No schemas found in {catalog}")
                    return

                schema = st.selectbox(
                    "Select schema",
                    schema_names,
                    key="selected_schema",
                    label_visibility="collapsed"
                )
            except Exception as e:
                st.error(f"Error loading schemas: {str(e)}")
                return
        else:
            schema = None

    with col3:
        st.markdown(":material/table_chart: **Tables**")
        if catalog and schema:
            try:
                tables = catalog_service.get_tables(catalog, schema)
                table_names = [t[0] for t in tables]

                if not table_names:
                    st.warning(f"No tables found in {catalog}.{schema}")
                    return

                # Use multiselect for bulk operations
                selected_tables = st.multiselect(
                    "Select tables",
                    table_names,
                    key="selected_tables",
                    help="Select one or more tables to document",
                    placeholder="Choose tables..."
                )
            except Exception as e:
                st.error(f"Error loading tables: {str(e)}")
                return
        else:
            selected_tables = []

    # Show queue management section
    _render_queue_section(state, catalog, schema, catalog_service, profile_service, connection)

    # Show table actions when selected
    if catalog and schema and selected_tables:
        st.divider()

        # Handle single vs multiple table selection
        if len(selected_tables) == 1:
            # Single table: Show full details (existing flow)
            table = selected_tables[0]
            table_id = TableIdentifier(catalog=catalog, schema=schema, table=table)

            with st.status("Loading table metadata...", expanded=True) as status:
                try:
                    status.update(label="Fetching table structure...")
                    # Build comprehensive table context using catalog service
                    table_context = catalog_service.get_table_context(catalog, schema, table)

                    if not table_context:
                        status.update(label="Failed to load metadata", state="error")
                        st.error("Could not load table metadata")
                        return

                    status.update(label="Complete!", state="complete")

                    # Display table info
                    st.markdown(f"**{catalog}.{schema}.{table}**")

                    # Metadata cards
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Columns", len(table_context['columns']))
                    with col_b:
                        if table_context.get('row_count'):
                            st.metric("Rows", f"{table_context['row_count']:,}")
                    with col_c:
                        st.metric("Type", table_context.get('table_type', 'TABLE'))

                    # Existing comment
                    if table_context.get('existing_comment'):
                        st.info(f"**Existing Comment:** {table_context['existing_comment']}", icon=":material/comment:")
                    else:
                        st.warning("No existing table comment", icon=":material/warning:")

                    # Data profile section
                    st.divider()

                    # Check if profile already generated using ProfileService
                    if not profile_service.has_profile(catalog, schema, table):
                        # Profile not generated yet - Highlight importance
                        st.info(
                            "💡 **Recommended:** Generate a data profile to reduce interview questions by 50-70%",
                            icon=":material/analytics:"
                        )

                        col_btn1, col_btn2 = st.columns([1, 3])
                        with col_btn1:
                            if st.button(BUTTON_GENERATE_PROFILE, type="primary", use_container_width=True, icon=ICON_ANALYTICS):
                                with st.status("Generating data profile...", expanded=True) as status:
                                    status.update(label="Analyzing table statistics...")
                                    success, profile_data, error = profile_service.generate_profile(
                                        connection, catalog, schema, table, table_context['columns']
                                    )

                                    if success:
                                        num_columns = len(profile_data.get('profile', {}).get('column_profiles', {}))
                                        status.update(label=f"Profile complete! Analyzed {num_columns} columns", state="complete")
                                        st.toast("Profile generated", icon=":material/check:")
                                        # Display warnings if any
                                        if profile_data and profile_data.get('profile', {}).get('table_stats', {}).get('errors'):
                                            for err in profile_data['profile']['table_stats']['errors']:
                                                st.warning(err, icon=":material/warning:")
                                        st.rerun()
                                    else:
                                        status.update(label="Profile generation failed", state="error")
                                        st.error(f"❌ Profile generation failed: {error}")

                                        # Add retry and skip options
                                        col_retry, col_skip = st.columns(2)
                                        with col_retry:
                                            if st.button("Retry", use_container_width=True):
                                                # Clear error state to trigger actual retry
                                                st.session_state.pop('_profile_error', None)
                                                st.rerun()

                                        with col_skip:
                                            if st.button("Skip Profile", use_container_width=True):
                                                st.info("You can still document this table, but interviews will be longer")
                                                st.caption("Profiles help reduce questions by 50-70%")

                        with col_btn2:
                            st.metric("Time Savings", "~3-5 min per table",
                                     help="Profiling pre-fills 50-70% of fields, reducing interview time")
                            st.caption("Profile generation: 2-5 seconds")

                    else:
                        # Profile already generated - show it
                        profile_data = profile_service.get_profile(catalog, schema, table)
                        profile_summary = profile_data.get('summary', '')

                        # Add to table context for interview
                        table_context['profile_summary'] = profile_summary

                        with st.expander("View Data Profile", expanded=False, icon=":material/bar_chart:"):
                            st.markdown(profile_summary)

                            # Show tip about what this does
                            st.info(
                                "This profile will be included in the LLM prompt to reduce "
                                "the number of questions needed during the interview.",
                                icon=":material/lightbulb:"
                            )

                            # Option to regenerate
                            if st.button("Regenerate Profile", key="regen_profile", icon=":material/refresh:"):
                                profile_service.clear_profile(catalog, schema, table)
                                st.rerun()

                    # Column details
                    with st.expander("View Columns", expanded=False, icon=":material/view_column:"):
                        for col in table_context['columns']:
                            col_display = f"**{col['name']}** (`{col['type']}`)"
                            if not col.get('nullable', True):
                                col_display += " NOT NULL"
                            st.markdown(col_display)
                            if col.get('comment'):
                                st.caption(col['comment'])
                            st.divider()

                    # Additional info
                    with st.expander("Additional Information", icon=":material/info:"):
                        if table_context.get('created'):
                            st.write(f"**Created:** {table_context['created']}")
                            if table_context.get('created_by'):
                                st.write(f"**Created by:** {table_context['created_by']}")
                        if table_context.get('last_altered'):
                            st.write(f"**Last modified:** {table_context['last_altered']}")
                            if table_context.get('last_altered_by'):
                                st.write(f"**Modified by:** {table_context['last_altered_by']}")
                        if table_context.get('data_format'):
                            st.write(f"**Format:** {table_context['data_format']}")

                    # Action buttons
                    st.divider()

                    # Show warning if profile not generated
                    has_profile = profile_service.has_profile(catalog, schema, table)
                    if not has_profile:
                        st.warning(
                            "Tip: Generate a data profile first for better interviews. "
                            "The LLM will ask 50-70% fewer questions.",
                            icon=":material/lightbulb:"
                        )

                    # Two workflow options: Single table or Multi-table
                    col1, col2 = st.columns(2)

                    # Build profile key for backwards compatibility
                    profile_key = f"{state.session_key}:profile_{table_id.key}" if has_profile else None

                    with col1:
                        # Check if table already in queue
                        queue = state.get_table_queue()
                        table_key = f"{catalog}_{schema}_{table}"
                        is_in_queue = any(
                            f"{t['catalog']}_{t['schema']}_{t['table']}" == table_key
                            for t in queue
                        )

                        button_label = "Already in Queue" if is_in_queue else "Add to Queue"
                        button_disabled = is_in_queue
                        button_type = "secondary" if is_in_queue else "primary"

                        if st.button(
                            button_label,
                            use_container_width=True,
                            type=button_type,
                            icon=":material/add:",
                            disabled=button_disabled
                        ):
                            # Add profile to context if available
                            if has_profile:
                                profile_data = profile_service.get_profile(catalog, schema, table)
                                table_context['profile_summary'] = profile_data.get('summary', '')

                            # Add to queue using StateManager
                            table_entry = {
                                'catalog': catalog,
                                'schema': schema,
                                'table': table,
                                'metadata': table_context,
                                'profile_key': profile_key
                            }

                            if state.add_to_queue(table_entry):
                                st.toast(f"Added {table} to queue", icon=":material/check:")
                            else:
                                st.toast(f"Table {table} already in queue", icon=":material/info:")
                            st.rerun()

                    with col2:
                        # Single-table quick start (adds to queue and starts immediately)
                        if st.button(BUTTON_START_INTERVIEW, type="primary", use_container_width=True, icon=ICON_FORWARD):
                            # Add profile to context if available
                            if has_profile:
                                profile_data = profile_service.get_profile(catalog, schema, table)
                                table_context['profile_summary'] = profile_data.get('summary', '')

                            # Clear queue and add just this table
                            state.set_table_queue([{
                                'catalog': catalog,
                                'schema': schema,
                                'table': table,
                                'metadata': table_context,
                                'profile_key': profile_key
                            }])
                            state.set_current_table_index(0)
                            state.set_workflow_step('table_interview')
                            st.session_state['selected_page'] = 'Document'
                            st.rerun()

                except Exception as e:
                    st.error(f"Error loading table details: {str(e)}")
                    import traceback
                    with st.expander("Error details"):
                        st.code(traceback.format_exc())

        else:
            # Multiple tables selected: Show summary and bulk actions
            st.markdown(f"**Selected: {len(selected_tables)} tables**")

            # Show table list
            with st.expander("View selected tables", expanded=False):
                for table_name in selected_tables:
                    st.caption(f"• {catalog}.{schema}.{table_name}")

            st.divider()

            # Bulk actions
            # Check which tables are already in queue
            in_queue, not_in_queue = _check_tables_in_queue(state, catalog, schema, selected_tables)

            col1, col2 = st.columns(2)

            with col1:
                # Determine button state based on queue status
                if len(not_in_queue) == 0:
                    # All selected tables already in queue
                    button_label = f"All {len(selected_tables)} Already in Queue"
                    button_disabled = True
                    button_type = "secondary"
                else:
                    # Some or all tables not in queue
                    button_label = f"Add {len(not_in_queue)} to Queue"
                    button_disabled = False
                    button_type = "primary"

                # Show info if some tables are already queued
                if len(in_queue) > 0 and len(not_in_queue) > 0:
                    st.caption(f"ℹ️ {len(in_queue)} table(s) already in queue")

                if st.button(
                    button_label,
                    use_container_width=True,
                    type=button_type,
                    icon=":material/add:",
                    disabled=button_disabled
                ):
                    added_count = 0
                    with st.status(f"Adding {len(not_in_queue)} tables...", expanded=True) as status:
                        for idx, table_name in enumerate(not_in_queue):
                            status.update(label=f"Processing {idx+1}/{len(not_in_queue)}: {table_name}")
                            try:
                                table_context = catalog_service.get_table_context(catalog, schema, table_name)
                                table_entry = {
                                    'catalog': catalog,
                                    'schema': schema,
                                    'table': table_name,
                                    'metadata': table_context,
                                    'profile_key': None
                                }
                                if state.add_to_queue(table_entry):
                                    added_count += 1
                            except Exception as e:
                                logger.error(f"Failed to add {table_name}: {e}")

                        status.update(label=f"Added {added_count} tables to queue", state="complete")

                    st.success(f"Added {added_count} table{'s' if added_count != 1 else ''} to queue!")
                    st.rerun()

            with col2:
                if st.button(
                    "Add & Start Now",
                    use_container_width=True,
                    icon=":material/play_arrow:"
                ):
                    # Add all to queue and start immediately
                    for table_name in selected_tables:
                        try:
                            table_context = catalog_service.get_table_context(catalog, schema, table_name)
                            table_entry = {
                                'catalog': catalog,
                                'schema': schema,
                                'table': table_name,
                                'metadata': table_context,
                                'profile_key': None
                            }
                            state.add_to_queue(table_entry)
                        except Exception as e:
                            logger.error(f"Failed to add {table_name}: {e}")

                    state.set_current_table_index(0)
                    state.set_workflow_step('table_interview')
                    st.session_state['selected_page'] = 'Document'
                    st.rerun()

    # Queue display now handled by _render_queue_section() above
