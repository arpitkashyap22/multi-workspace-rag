"""
Sidebar module.
Renders user session details, workspace selector, and workspace creation tools.
"""

from typing import Tuple
import streamlit as st
from src.database import repository
from src.services import rag


@st.dialog("Delete Workspace Confirmation")
def confirm_delete_workspace_dialog(user_id: str, workspace_id: str, workspace_name: str) -> None:
    """
    Renders a confirmation modal with explicit warnings before permanently deleting a workspace.
    """
    st.warning(f"⚠️ Are you sure you want to delete workspace **{workspace_name}**?")
    st.error(
        "**CRITICAL WARNING: Irreversible Cascading Deletion**\n\n"
        "Deleting this workspace will permanently and irreversibly remove:\n"
        "• **All uploaded documents** (.pdf, .txt, .md) stored in Neon Object Storage\n"
        "• **All vector embeddings** and semantic chunks in PostgreSQL pgvector\n"
        "• **All workspace tasks**, action items, and task logs\n"
        "• **All tool audit execution records** for this workspace\n"
        "• **Conversation and chat history** for this workspace\n\n"
        "**This action cannot be undone.**"
    )

    col_cancel, col_confirm = st.columns(2)
    with col_cancel:
        if st.button("Cancel", width="stretch", key=f"dlg_ws_cancel_{workspace_id}"):
            st.rerun()

    with col_confirm:
        if st.button(
            "🚨 Yes, Delete Permanently",
            type="primary",
            width="stretch",
            key=f"dlg_ws_confirm_{workspace_id}",
        ):
            with st.spinner(f"Deleting workspace '{workspace_name}' and all associated assets..."):
                try:
                    rag.delete_workspace_pipeline(user_id=user_id, workspace_id=workspace_id)

                    # Clear chat history in session state for this workspace
                    if "chat_histories" in st.session_state and workspace_id in st.session_state.chat_histories:
                        del st.session_state.chat_histories[workspace_id]
                    if "active_conversation_id" in st.session_state:
                        st.session_state.pop("active_conversation_id", None)

                    # If the deleted workspace was the active one, update active_workspace_id
                    if st.session_state.get("active_workspace_id") == workspace_id:
                        remaining_workspaces = repository.get_user_workspaces(user_id)
                        if remaining_workspaces:
                            st.session_state.active_workspace_id = remaining_workspaces[0]["id"]
                        else:
                            new_ws = repository.create_workspace(user_id, "General")
                            st.session_state.active_workspace_id = new_ws["id"]

                    st.toast(f"Workspace '{workspace_name}' and all associated assets deleted.", icon="🗑️")
                    st.rerun()
                except Exception as err:
                    st.error(f"Failed to delete workspace: {err}")


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
            st.cache_data.clear()
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

        # Quick Delete button for Active Workspace
        if st.button(
            f"🗑️ Delete '{active_ws_name}'",
            key="btn_delete_active_ws",
            width="stretch",
            type="secondary",
            help=f"Permanently delete active workspace '{active_ws_name}' and all its data.",
        ):
            confirm_delete_workspace_dialog(
                user_id=user_id,
                workspace_id=st.session_state.active_workspace_id,
                workspace_name=active_ws_name,
            )

        # Add New Workspace
        with st.expander("➕ Create Workspace", expanded=False):
            new_ws_name = st.text_input("Workspace Name", placeholder="e.g. Finance, Research", key="input_new_ws_name")
            if st.button("Create Workspace", width="stretch", type="secondary", key="btn_create_ws"):
                if new_ws_name.strip():
                    with st.spinner("Creating workspace..."):
                        created_ws = repository.create_workspace(user_id, new_ws_name.strip())
                        st.session_state.active_workspace_id = created_ws["id"]
                        st.toast(f"Created workspace '{created_ws['name']}'!", icon="✨")
                        st.rerun()
                else:
                    st.warning("Please provide a valid workspace name.")

        # Manage / List all workspaces
        with st.expander(f"📋 List of Workspaces ({len(workspaces)})", expanded=False):
            st.caption("Manage all your workspaces. Deleting a workspace permanently purges its files, vectors, and logs.")
            for ws in workspaces:
                ws_id = ws["id"]
                ws_name = ws["name"]
                is_active = (ws_id == st.session_state.active_workspace_id)

                with st.container():
                    col_ws_name, col_ws_del = st.columns([4, 1])
                    with col_ws_name:
                        active_indicator = " 🟢 *(Active)*" if is_active else ""
                        st.markdown(f"**📁 {ws_name}**{active_indicator}")
                    with col_ws_del:
                        if st.button(
                            "🗑️",
                            key=f"del_list_ws_{ws_id}",
                            help=f"Delete workspace '{ws_name}'",
                        ):
                            confirm_delete_workspace_dialog(
                                user_id=user_id,
                                workspace_id=ws_id,
                                workspace_name=ws_name,
                            )
                    st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid rgba(255,255,255,0.08);'>", unsafe_allow_html=True)

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
