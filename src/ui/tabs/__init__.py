"""
UI Tabs package: chat assistant, documents manager, and operational dashboard.
"""

from .chat_tab import render_chat_tab
from .documents_tab import render_documents_tab
from .dashboard_tab import render_dashboard_tab


__all__ = [
    "render_chat_tab",
    "render_documents_tab",
    "render_dashboard_tab",
]
