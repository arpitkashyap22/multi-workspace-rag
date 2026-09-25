"""
Multi-Workspace Document Assistant with Tool Calling & Scoped RAG.
Main Streamlit application entry point orchestrating UI presentation and domain services.
"""

import sys
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

# Ensure project root and src directory are on sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

load_dotenv()

from src.ui.styles import apply_custom_styles
from src.ui.auth import render_auth_gate
from src.ui.sidebar import render_sidebar
from src.ui.tabs import render_chat_tab, render_documents_tab, render_dashboard_tab

# Page Configuration
st.set_page_config(
    page_title="Multi-Workspace Document Assistant",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply Modern Theme Tokens
apply_custom_styles()

# Authentication Gate
if not render_auth_gate():
    st.stop()

# Sidebar: User Session & Workspace Switcher
active_ws_id, active_ws_name = render_sidebar()

# Main Workspace Header
st.markdown(
    f"""
    <div style='display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;'>
        <div>
            <div class="ws-badge">🔒 Workspace Scoped: {active_ws_name}</div>
            <h1 style='margin: 0; font-size: 1.85rem; font-weight: 700;'>Document Intelligence Hub</h1>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Tabs Interface
tab_chat, tab_docs, tab_dashboard = st.tabs(
    ["💬 Assistant", "📁 Documents", "📊 Dashboard & Logs"]
)

with tab_chat:
    render_chat_tab(active_ws_id, active_ws_name)

with tab_docs:
    render_documents_tab(active_ws_id, active_ws_name)

with tab_dashboard:
    render_dashboard_tab(active_ws_id, active_ws_name)
