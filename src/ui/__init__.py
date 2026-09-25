"""
UI package for Streamlit presentation layer.
"""

from .styles import apply_custom_styles
from .auth import render_auth_gate
from .sidebar import render_sidebar
from .tabs import render_chat_tab, render_documents_tab, render_dashboard_tab

__all__ = [
    "apply_custom_styles",
    "render_auth_gate",
    "render_sidebar",
    "render_chat_tab",
    "render_documents_tab",
    "render_dashboard_tab",
]
