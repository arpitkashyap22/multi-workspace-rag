"""
Sidebar module.
Renders user session details, workspace selector, and workspace creation tools.
"""

from typing import Tuple
import streamlit as st
from src.database import repository


def render_sidebar() -> Tuple[str, str]:
    """
    Renders the sidebar navigation and workspace management controls.

    Returns:
        tuple[str, str]: (active_workspace_id, active_workspace_name)
    """
    current_user = st.session_state.user
    user_id = current_user["id"]
    user_email = current_user["email"]

    # Fetch existing workspaces for user
    workspaces = repository.get_user_workspaces(user_id)
    if not workspaces:
        default_ws = repository.create_workspace(user_id, "General")
        workspaces = [default_ws]

    ws_map = {w["id"]: w["name"] for w in workspaces}

    # Ensure valid active_workspace_id
    if (
        "active_workspace_id" not in st.session_state
        or st.session_state.active_workspace_id not in ws_map
    ):
        st.session_state.active_workspace_id = workspaces[0]["id"]

    with st.sidebar:
        st.markdown(
            f"""
            <div style='padding: 0.5rem 0 1.25rem 0;'>
                <div style='font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; margin-bottom: 4px;'>Logged in as</div>
                <div style='font-size: 0.95rem; font-weight: 600; color: #f8fafc; word-break: break-all;'>{user_email}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("🚪 Logout", width="stretch"):
            st.session_state.clear()
            st.rerun()

        st.divider()

        st.markdown("### 🏢 Workspaces")

        # Select Active Workspace
        selected_ws_id = st.selectbox(
            "Active Workspace",
            options=list(ws_map.keys()),
            format_func=lambda wid: f"📁 {ws_map[wid]}",
            index=list(ws_map.keys()).index(st.session_state.active_workspace_id),
            help="All document uploads, RAG queries, and task logs are strictly isolated to this workspace.",
        )

        if selected_ws_id != st.session_state.active_workspace_id:
            st.session_state.active_workspace_id = selected_ws_id
            st.rerun()

        active_ws_name = ws_map[st.session_state.active_workspace_id]

        # Add New Workspace
        with st.expander("➕ Create Workspace", expanded=False):
            new_ws_name = st.text_input("Workspace Name", placeholder="e.g. Finance, Research")
            if st.button("Create Workspace", width="stretch", type="secondary"):
                if new_ws_name.strip():
                    with st.spinner("Creating workspace..."):
                        created_ws = repository.create_workspace(user_id, new_ws_name.strip())
                        st.session_state.active_workspace_id = created_ws["id"]
                        st.success(f"Created '{created_ws['name']}'!")
                        st.rerun()
                else:
                    st.warning("Please provide a valid workspace name.")

        st.divider()
        st.markdown(
            """
            <div style='font-size: 0.8rem; color: #64748b;'>
                <b>Tenancy Isolation:</b><br>
                All data queries enforce <code>WHERE workspace_id = %s</code> at the Postgres SQL layer.
            </div>
            """,
            unsafe_allow_html=True,
        )

    return st.session_state.active_workspace_id, active_ws_name
