"""
Dashboard Tab module.
Renders real-time operational task metrics and tool audit logs
scoped to the active workspace with fragment-level live refresh.
"""

import streamlit as st
from src.database import repository


@st.fragment
def render_dashboard_tab(active_ws_id: str, active_ws_name: str) -> None:
    """
    Renders real-time tasks and tool audit logs for the active workspace.
    Uses @st.fragment so refreshing dashboard metrics does not trigger full app reruns.

    Args:
        active_ws_id: UUID of the current active workspace.
        active_ws_name: Display name of the active workspace.
    """
    col_head_title, col_head_btn = st.columns([4, 1])
    with col_head_title:
        st.markdown("### 📊 Operational Dashboard & Audit Trail")
        st.caption(f"Real-time operational records scoped strictly to **{active_ws_name}**.")
    with col_head_btn:
        if st.button("🔄 Refresh Data", width="stretch", key="btn_refresh_dashboard"):
            try:
                repository.get_workspace_tasks.clear()
                repository.get_tool_logs.clear()
            except Exception:
                pass
            st.rerun()

    # Fetch Tasks & Logs (cached)
    tasks = repository.get_workspace_tasks(active_ws_id)
    logs = repository.get_tool_logs(active_ws_id)

    col_dash_left, col_dash_right = st.columns(2)

    # Tasks Section
    with col_dash_left:
        st.markdown(f"#### 📌 Tasks (`workspace_tasks`) — Total: {len(tasks)}")
        if tasks:
            high_count = sum(1 for t in tasks if t.get("priority") == "high")
            med_count = sum(1 for t in tasks if t.get("priority") == "medium")
            low_count = sum(1 for t in tasks if t.get("priority") == "low")

            mcol1, mcol2, mcol3 = st.columns(3)
            mcol1.metric("High Priority", high_count)
            mcol2.metric("Medium Priority", med_count)
            mcol3.metric("Low Priority", low_count)

            formatted_tasks = [
                {
                    "Title": t["title"],
                    "Priority": str(t["priority"]).upper(),
                    "Created At": t["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                    if hasattr(t["created_at"], "strftime")
                    else str(t["created_at"]),
                    "Task ID": t["id"][:8] + "...",
                }
                for t in tasks
            ]
            st.dataframe(
                formatted_tasks,
                width="stretch",
                hide_index=True,
                column_config={
                    "Title": st.column_config.TextColumn("Title", width="large"),
                    "Priority": st.column_config.TextColumn("Priority", width="small"),
                    "Created At": st.column_config.TextColumn("Created At", width="medium"),
                    "Task ID": st.column_config.TextColumn("ID", width="small"),
                },
            )
        else:
            st.info("No tasks recorded in this workspace. Ask the assistant to create tasks via chat!")

    # Tool Execution Logs Section
    with col_dash_right:
        st.markdown(f"#### 🛡️ Audit Logs (`tool_logs`) — Total: {len(logs)}")
        if logs:
            success_count = sum(1 for l in logs if l.get("status") == "SUCCESS")
            failed_count = sum(1 for l in logs if l.get("status") == "FAILED")

            lcol1, lcol2 = st.columns(2)
            lcol1.metric("Successful Executions", success_count)
            lcol2.metric("Failed Executions", failed_count)

            formatted_logs = [
                {
                    "Tool": l["tool_name"],
                    "Status": l["status"],
                    "Arguments": str(l["arguments"]),
                    "Time": l["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                    if hasattr(l["created_at"], "strftime")
                    else str(l["created_at"]),
                }
                for l in logs
            ]
            st.dataframe(
                formatted_logs,
                width="stretch",
                hide_index=True,
                column_config={
                    "Tool": st.column_config.TextColumn("Tool Name", width="medium"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                    "Arguments": st.column_config.TextColumn("Parameters", width="large"),
                    "Time": st.column_config.TextColumn("Logged At", width="medium"),
                },
            )
        else:
            st.info("No tool executions logged yet in this workspace.")
