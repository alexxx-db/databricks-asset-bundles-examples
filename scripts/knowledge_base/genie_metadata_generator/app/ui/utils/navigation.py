"""
Workflow navigation utilities.
Atomic functions for managing workflow state and navigation.
"""
import streamlit as st
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def navigate_to_workflow_step(step: str, clear_state: bool = False):
    """
    Atomic workflow navigation function.

    Args:
        step: Target workflow step ('browse', 'table_interview', 'review', 'genie_interview', 'export', 'library')
        clear_state: If True, clear interview state before navigating
    """
    from state import get_state_manager

    # Validate step
    valid_steps = ['browse', 'table_interview', 'review', 'genie_interview', 'export', 'library']
    if step not in valid_steps:
        logger.warning(f"Invalid workflow step: {step}")
        return

    state = get_state_manager()

    # Clear state if requested
    if clear_state:
        state.clear_table_interview()
        state.clear_genie_interview()
        logger.debug(f"Cleared interview state before navigating to {step}")

    # Navigate
    state.set_workflow_step(step)
    logger.info(f"Navigated to workflow step: {step}")
    st.rerun()


def render_back_button(target_step: str, label: str = "Back", icon: str = ":material/arrow_back:", key: Optional[str] = None):
    """
    Reusable back button component.

    Args:
        target_step: Workflow step to navigate to
        label: Button label
        icon: Material icon
        key: Unique key for button (auto-generated if None)

    Returns:
        True if button was clicked (for conditional logic)
    """
    if key is None:
        key = f"back_to_{target_step}"

    if st.button(label, use_container_width=True, icon=icon, key=key):
        navigate_to_workflow_step(target_step)
        return True
    return False
