"""
Interview service for managing interview lifecycle and operations atomically.

Single source of truth for interview operations with proper state coordination.
"""
import logging
from typing import Optional

from llm.client import LLMClient
from llm.section_interview import SectionBasedInterview
from state import StateManager

from .context_summarizer_service import ContextSummarizerService

logger = logging.getLogger(__name__)


class InterviewService:
    """Service for managing interview lifecycle with atomic operations."""

    def __init__(self, state_manager: StateManager, context_summarizer: ContextSummarizerService):
        """
        Initialize interview service.

        Args:
            state_manager: StateManager instance for state coordination
            context_summarizer: ContextSummarizerService for handling large contexts
        """
        self.state = state_manager
        self.context_summarizer = context_summarizer

    def _get_llm_client(self) -> LLMClient:
        """Get cached LLM client for interviews."""
        from llm.client import get_main_llm_client
        return get_main_llm_client()

    def _hydrate_profile(self, table_data: dict, connection=None) -> dict:
        """
        Ensure profile_summary is in table_data.

        Strategy (3-tier fallback):
        1. Check metadata (fast) - use if already present
        2. Check StateManager (medium) - fetch if cached
        3. Auto-generate (slow but complete) - generate if connection available

        This handles app restarts and ensures profiles reach section questions.

        Args:
            table_data: Dict with catalog, schema, table, and optional metadata
            connection: Optional DB connection for auto-generation

        Returns:
            table_data with hydrated profile_summary (if available)
        """
        from state import TableIdentifier

        # Step 1: Check if profile already in metadata
        metadata = table_data.get('metadata', {})
        if metadata.get('profile_summary'):
            profile_len = len(metadata['profile_summary'])
            logger.debug(f"Profile already in metadata for {table_data.get('table')} ({profile_len} chars)")
            return table_data

        # Step 2: Try to fetch from StateManager
        try:
            table_id = TableIdentifier(
                catalog=table_data['catalog'],
                schema=table_data['schema'],
                table=table_data['table']
            )

            if self.state.has_profile(table_id):
                profile_data = self.state.get_profile(table_id)
                if profile_data and 'summary' in profile_data:
                    # Hydrate from StateManager
                    if 'metadata' not in table_data:
                        table_data['metadata'] = {}

                    table_data['metadata']['profile_summary'] = profile_data['summary']
                    profile_len = len(profile_data['summary'])
                    logger.info(
                        f"✓ Hydrated profile from StateManager for {table_data['table']} "
                        f"({profile_len} chars)"
                    )
                    return table_data
                else:
                    logger.warning(f"Profile exists but missing summary for {table_data['table']}")

            # Step 3: Auto-generate if not found and connection available
            if connection:
                logger.info(f"Profile not found for {table_data['table']}, auto-generating...")

                from state.services import get_profile_service
                profile_service = get_profile_service(self.state)

                columns = table_data.get('metadata', {}).get('columns', [])
                if not columns:
                    logger.warning(f"No columns in metadata for {table_data['table']}, cannot auto-generate profile")
                    return table_data

                success, profile_data, error = profile_service.generate_profile(
                    connection,
                    table_data['catalog'],
                    table_data['schema'],
                    table_data['table'],
                    columns,
                    table_data  # This will be updated in-place by ProfileService
                )

                if success and profile_data:
                    logger.info(
                        f"✓ Auto-generated profile for {table_data['table']} "
                        f"({len(profile_data['summary'])} chars)"
                    )
                else:
                    logger.warning(f"Failed to auto-generate profile for {table_data['table']}: {error}")
            else:
                logger.debug(f"No profile found for {table_data['table']} and no connection to generate")

        except Exception as e:
            logger.warning(f"Failed to hydrate profile for {table_data.get('table')}: {e}")

        return table_data

    def _hydrate_profiles_batch(self, completed_tables: list, connection=None) -> list:
        """
        Hydrate profiles for multiple tables (used in Genie interviews).

        Args:
            completed_tables: List of table data dicts
            connection: Optional DB connection for auto-generation

        Returns:
            List of table data dicts with hydrated profiles
        """
        logger.debug(f"Starting batch hydration for {len(completed_tables)} tables")

        hydrated_tables = []
        for idx, table_data in enumerate(completed_tables, 1):
            table_name = table_data.get('table', 'unknown')
            logger.debug(f"[{idx}/{len(completed_tables)}] Hydrating {table_name}")

            hydrated_table = self._hydrate_profile(table_data, connection)

            # Debug: Check if profile was added
            has_profile = bool(hydrated_table.get('metadata', {}).get('profile_summary'))
            logger.debug(f"[{idx}/{len(completed_tables)}] {table_name} - profile present: {has_profile}")

            hydrated_tables.append(hydrated_table)

        logger.debug(f"Batch hydration complete: {len(hydrated_tables)} tables processed")
        return hydrated_tables

    def start_table_interview(
        self,
        table_data: dict,
        interview_type: str = 'new',
        connection=None
    ) -> Optional[SectionBasedInterview]:
        """
        Start a table interview atomically with auto-profile generation.

        Args:
            table_data: Dict with catalog, schema, table, metadata
            interview_type: 'new' | 'reinterview' | 'edit'
            connection: Optional DB connection for auto-profiling

        Returns:
            SectionBasedInterview instance or None on failure
        """
        from config import config

        try:
            # CRITICAL: Hydrate profile (with optional auto-generation)
            # This ensures profiles survive app restarts and generates if missing
            table_data = self._hydrate_profile(table_data, connection)

            # Get LLM client
            llm = self._get_llm_client()

            # Load table comment section config
            config_path = config.tier1_sections_config_path

            # Create section interview WITH context summarizer
            interview = SectionBasedInterview(
                llm,
                config_path,
                context_summarizer=self.context_summarizer
            )

            # Start interview with planning step (now with hydrated profile!)
            interview.start_interview(table_data)

            # Log planning results
            planning = interview.get_planning_summary()
            if planning:
                logger.info(
                    f"Table interview started: {planning['pre_populated_count']} pre-filled, "
                    f"{planning['questions_count']} questions"
                )

            # Persist to state
            self.state.set_table_interview(interview)

            return interview

        except Exception as e:
            logger.error(f"Failed to start table interview: {e}", exc_info=True)
            return None

    def start_genie_interview(
        self,
        completed_tables: list,
        source: str = 'current',
        connection=None
    ) -> Optional[SectionBasedInterview]:
        """
        Start a Genie interview atomically with auto-profile generation.

        Args:
            completed_tables: List of completed table data dicts
            source: 'current' | 'library' | 'restored'
            connection: Optional DB connection for auto-profiling

        Returns:
            SectionBasedInterview instance or None on failure
        """
        from config import config

        if not completed_tables:
            logger.warning("No completed tables provided for Genie interview")
            return None

        try:
            # CRITICAL: Hydrate profiles for all tables (with optional auto-generation)
            # This ensures profiles survive app restarts and generates if missing
            completed_tables = self._hydrate_profiles_batch(completed_tables, connection)

            # CRITICAL FIX: Update StateManager with hydrated tables
            # This ensures any future get_completed_tables() calls have the profiles
            for table_data in completed_tables:
                self.state.add_completed_table(table_data)

            logger.info(f"Updated StateManager with {len(completed_tables)} hydrated tables")

            # Debug: Verify profiles are in completed_tables before passing to interview
            for table_data in completed_tables:
                table_name = table_data.get('table', 'unknown')
                profile_summary = table_data.get('metadata', {}).get('profile_summary')
                if profile_summary:
                    logger.debug(f"✓ Passing {table_name} to interview with profile ({len(profile_summary)} chars)")
                else:
                    logger.warning(f"⚠ Passing {table_name} to interview WITHOUT profile")

            # Get LLM client
            llm = self._get_llm_client()

            # Load genie section config
            config_path = config.tier2_sections_config_path

            # Create section interview WITH context summarizer
            interview = SectionBasedInterview(
                llm,
                config_path,
                context_summarizer=self.context_summarizer
            )

            # Start interview with all completed tables (now with hydrated profiles!)
            interview.start_interview(completed_tables)

            # Log planning results
            planning = interview.get_planning_summary()
            if planning:
                logger.info(
                    f"Genie interview started: {planning['pre_populated_count']} pre-filled, "
                    f"{planning['questions_count']} questions"
                )

            # Persist to state
            self.state.set_genie_interview(interview)

            return interview

        except Exception as e:
            logger.error(f"Failed to start Genie interview: {e}", exc_info=True)
            return None

    def answer_question(
        self,
        interview: SectionBasedInterview,
        answer: str,
        interview_type: str
    ) -> Optional[str]:
        """
        Answer a question atomically with auto-save.

        Args:
            interview: SectionBasedInterview instance
            answer: User's response
            interview_type: 'table' or 'genie'

        Returns:
            Next question or None on failure
        """
        try:
            # Process answer
            response = interview.answer_question(answer)

            # Auto-save every 3 Q&A pairs (6 messages)
            if len(interview.conversation_history) % 6 == 0:
                self.save_interview_progress(interview, interview_type)
                logger.info(f"Auto-saved {interview_type} interview at {len(interview.conversation_history)} messages")
            else:
                # Regular save
                self.save_interview_progress(interview, interview_type)

            return response

        except Exception as e:
            logger.error(f"Failed to answer question: {e}", exc_info=True)
            # Still try to save progress
            self.save_interview_progress(interview, interview_type)
            raise

    def complete_section(
        self,
        interview: SectionBasedInterview,
        interview_type: str,
        section_yaml: Optional[str] = None
    ) -> Optional[str]:
        """
        Complete current section atomically.

        Args:
            interview: SectionBasedInterview instance
            interview_type: 'table' or 'genie'
            section_yaml: Optional YAML content for this section

        Returns:
            First question of next section, or None if all done
        """
        try:
            # Complete the section
            next_question = interview.complete_section(section_yaml)

            # Save progress
            self.save_interview_progress(interview, interview_type)

            logger.info(f"Section completed, advanced to section {interview.current_section_idx}")

            return next_question

        except Exception as e:
            logger.error(f"Failed to complete section: {e}", exc_info=True)
            raise

    def skip_section(
        self,
        interview: SectionBasedInterview,
        interview_type: str
    ) -> Optional[str]:
        """
        Skip current section atomically.

        Args:
            interview: SectionBasedInterview instance
            interview_type: 'table' or 'genie'

        Returns:
            First question of next section, or None if all done
        """
        try:
            # Skip the section
            next_question = interview.skip_section()

            # Save progress
            self.save_interview_progress(interview, interview_type)

            logger.info(f"Section skipped, advanced to section {interview.current_section_idx}")

            return next_question

        except Exception as e:
            logger.error(f"Failed to skip section: {e}", exc_info=True)
            raise

    def generate_yaml(self, interview: SectionBasedInterview) -> str:
        """
        Generate final YAML atomically.

        Args:
            interview: SectionBasedInterview instance

        Returns:
            Merged YAML content
        """
        try:
            return interview.get_merged_yaml()
        except Exception as e:
            logger.error(f"Failed to generate YAML: {e}", exc_info=True)
            raise

    def save_interview_progress(
        self,
        interview: SectionBasedInterview,
        interview_type: str
    ) -> None:
        """
        Save interview progress to state.

        Args:
            interview: SectionBasedInterview instance
            interview_type: 'table' or 'genie'
        """
        try:
            if interview_type == 'table':
                self.state.set_table_interview(interview)
            elif interview_type == 'genie':
                self.state.set_genie_interview(interview)
            else:
                logger.warning(f"Unknown interview type: {interview_type}")
        except Exception as e:
            logger.error(f"Failed to save interview progress: {e}", exc_info=True)

    def finalize_table_interview(
        self,
        interview: SectionBasedInterview,
        table_data: dict
    ) -> bool:
        """
        Finalize table interview atomically - save YAML and update state.

        Args:
            interview: SectionBasedInterview instance
            table_data: Original table data

        Returns:
            True if successful, False otherwise
        """
        from datetime import datetime

        from state import TableIdentifier

        try:
            # Generate final YAML
            yaml_content = interview.get_merged_yaml()

            # Get profile data from state if available
            profile_summary = None
            profile_key = table_data.get('profile_key')
            if profile_key:
                table_id = TableIdentifier(
                    catalog=table_data['catalog'],
                    schema=table_data['schema'],
                    table=table_data['table']
                )
                profile_data = self.state.get_profile(table_id)
                if profile_data and 'summary' in profile_data:
                    profile_summary = profile_data['summary']

            # Fallback to metadata if not in state
            if not profile_summary:
                profile_summary = table_data.get('metadata', {}).get('profile_summary')

            # Build completed table entry
            table_name = f"{table_data['catalog']}.{table_data['schema']}.{table_data['table']}"
            table_entry = {
                'catalog': table_data['catalog'],
                'schema': table_data['schema'],
                'table': table_data['table'],
                'metadata': table_data.get('metadata', {}),
                'tier1_yaml': yaml_content,
                'table_name': table_name,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'profile_key': profile_key,
                'profile_summary': profile_summary
            }

            # Add to completed tables
            self.state.add_completed_table(table_entry)

            # Add to history for session tracking
            self.state.add_to_history({
                'catalog': table_data['catalog'],
                'schema': table_data['schema'],
                'table': table_data['table'],
                'tier1_yaml': yaml_content,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M")
            })

            # Clear the interview
            self.state.clear_table_interview()

            logger.info(f"Table interview finalized for {table_name}")

            return True

        except Exception as e:
            logger.error(f"Failed to finalize table interview: {e}", exc_info=True)
            return False

    def finalize_genie_interview(
        self,
        interview: SectionBasedInterview
    ) -> bool:
        """
        Finalize Genie interview atomically - save YAML and clear state.

        Args:
            interview: SectionBasedInterview instance

        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate final YAML
            yaml_content = interview.get_merged_yaml()

            # Save to state
            self.state.set_tier2_yaml(yaml_content)

            # Clear the interview
            self.state.clear_genie_interview()

            logger.info("Genie interview finalized")

            return True

        except Exception as e:
            logger.error(f"Failed to finalize Genie interview: {e}", exc_info=True)
            return False


def get_interview_service(state_manager: StateManager) -> InterviewService:
    """
    Get cached interview service instance.

    Args:
        state_manager: StateManager instance

    Returns:
        InterviewService instance
    """
    import streamlit as st

    from .context_summarizer_service import get_context_summarizer_service

    # Cache the service instance per session
    if '_interview_service' not in st.session_state:
        # Get LLM client for context summarizer (uses separate Gemini Flash endpoint)
        from llm.client import get_summarizer_llm_client
        llm_client = get_summarizer_llm_client()

        # Get context summarizer service (creates if not exists)
        context_summarizer = get_context_summarizer_service(llm_client)

        # Create interview service with dependencies
        st.session_state._interview_service = InterviewService(
            state_manager,
            context_summarizer
        )

    return st.session_state._interview_service
