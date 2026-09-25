"""
UI Tabs package: chat assistant, documents manager, and operational dashboard.
"""

from src.ui.tabs.chat_tab import render_chat_tab
from src.ui.tabs.documents_tab import render_documents_tab
from src.ui.tabs.dashboard_tab import render_dashboard_tab

__all__ = [
    "render_chat_tab",
    "render_documents_tab",
    "render_dashboard_tab",
]
