"""
UI package for Streamlit presentation layer.
"""

from src.ui.styles import apply_custom_styles
from src.ui.auth import render_auth_gate
from src.ui.sidebar import render_sidebar
from src.ui.tabs import render_chat_tab, render_documents_tab, render_dashboard_tab

__all__ = [
    "apply_custom_styles",
    "render_auth_gate",
    "render_sidebar",
    "render_chat_tab",
    "render_documents_tab",
    "render_dashboard_tab",
]
