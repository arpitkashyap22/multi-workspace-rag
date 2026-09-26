"""
Workspace Tasks database repository module.
Handles creation and retrieval of tasks strictly scoped by workspace_id.
"""

from typing import Any
import streamlit as st
from psycopg.rows import dict_row
from src.database.connection import get_db_connection


def save_task(workspace_id: str, title: str, priority: str) -> dict[str, Any]:
    """Insert a task into workspace_tasks strictly scoped to workspace_id."""
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO workspace_tasks (workspace_id, title, priority)
                VALUES (%s, %s, %s)
                RETURNING id, workspace_id, title, priority, created_at;
                """,
                (workspace_id, title.strip(), priority.lower()),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"Failed to save task '{title}': no row returned")

            try:
                get_workspace_tasks.clear()
            except Exception:
                pass

            return {
                "id": str(row["id"]),
                "workspace_id": str(row["workspace_id"]),
                "title": row["title"],
                "priority": row["priority"],
                "created_at": row["created_at"],
            }


@st.cache_data(ttl="15s", max_entries=50, show_spinner=False)
def get_workspace_tasks(workspace_id: str) -> list[dict[str, Any]]:
    """Retrieve all tasks belonging to the active workspace (cached for fast dashboard render)."""
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, workspace_id, title, priority, created_at FROM workspace_tasks WHERE workspace_id = %s ORDER BY created_at DESC;",
                (workspace_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": str(r["id"]),
                    "workspace_id": str(r["workspace_id"]),
                    "title": r["title"],
                    "priority": r["priority"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
