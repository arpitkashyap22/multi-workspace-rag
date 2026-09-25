"""
Dashboard Tab module.
Renders real-time operational task metrics and tool audit logs
scoped to the active workspace.
"""

import streamlit as st
from src.database import repository


def render_dashboard_tab(active_ws_id: str, active_ws_name: str) -> None:
    """
    Renders real-time tasks and tool audit logs for the active workspace.

    Args:
        active_ws_id: UUID of the current active workspace.
        active_ws_name: Display name of the active workspace.
    """
    st.markdown("### 📊 Workspace Dashboard & Execution Logs")
    st.caption(f"Real-time operational records scoped strictly to **{active_ws_name}**.")

    col_dash_left, col_dash_right = st.columns(2)

    # Fetch Tasks & Logs
    tasks = repository.get_workspace_tasks(active_ws_id)
    logs = repository.get_tool_logs(active_ws_id)

    # Tasks Table
    with col_dash_left:
        st.markdown(f"#### 📌 Tasks (`workspace_tasks`) — Total: {len(tasks)}")
        if tasks:
            # Summary Metrics
            high_count = sum(1 for t in tasks if t.get("priority") == "high")
            med_count = sum(1 for t in tasks if t.get("priority") == "medium")
            low_count = sum(1 for t in tasks if t.get("priority") == "low")

            mcol1, mcol2, mcol3 = st.columns(3)
            mcol1.metric("🔴 High", high_count)
            mcol2.metric("🟡 Medium", med_count)
            mcol3.metric("🟢 Low", low_count)

            # Format for DataFrame
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
            st.dataframe(formatted_tasks, width="stretch", hide_index=True)
        else:
            st.info("No tasks recorded in this workspace. Ask the assistant to create tasks via chat!")

    # Tool Execution Logs Table
    with col_dash_right:
        st.markdown(f"#### 🛡️ Audit Logs (`tool_logs`) — Total: {len(logs)}")
        if logs:
            success_count = sum(1 for l in logs if l.get("status") == "SUCCESS")
            failed_count = sum(1 for l in logs if l.get("status") == "FAILED")

            lcol1, lcol2 = st.columns(2)
            lcol1.metric("✅ Success", success_count)
            lcol2.metric("❌ Failed", failed_count)

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
            st.dataframe(formatted_logs, width="stretch", hide_index=True)
        else:
            st.info("No tool executions logged yet in this workspace.")
