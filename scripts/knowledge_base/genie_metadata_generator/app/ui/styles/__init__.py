"""
Centralized styles module for the Genify app.

Usage:
    from ui.styles import inject_app_styles

    # Call once at app startup
    inject_app_styles()
"""

import streamlit as st

from .components import COMPONENT_CSS
from .layout import LAYOUT_CSS
from .theme import THEME_CSS


def inject_app_styles():
    """
    Inject all global CSS styles into the Streamlit app.

    Call this once at app startup (in app.py) to load:
    - Theme variables (colors, spacing, dark mode)
    - Layout styles (full-height, scroll management)
    - Component styles (cards, steps, logo)
    """
    combined_css = f"""
    <style>
    {THEME_CSS}
    {LAYOUT_CSS}
    {COMPONENT_CSS}
    </style>
    """
    st.markdown(combined_css, unsafe_allow_html=True)


__all__ = ['inject_app_styles']
