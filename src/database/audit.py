"""
Audit and Tool Execution Logs database repository module.
Handles logging and retrieval of tool execution records strictly scoped by workspace_id.
"""

import json
from typing import Any
from psycopg.rows import dict_row
from src.database.connection import get_db_connection


def log_tool_execution(
    workspace_id: str | None,
    tool_name: str,
    arguments: dict[str, Any],
    status: str,
) -> None:
    """Log tool execution to tool_logs audit table."""
    if not workspace_id:
        return
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tool_logs (workspace_id, tool_name, arguments, status)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (workspace_id, tool_name, json.dumps(arguments), status),
                )
    except Exception as e:
        print(f"Warning: Failed to write to tool_logs: {e}")


def get_tool_logs(workspace_id: str) -> list[dict[str, Any]]:
    """Retrieve tool execution logs for the active workspace."""
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, workspace_id, tool_name, arguments, status, created_at FROM tool_logs WHERE workspace_id = %s ORDER BY created_at DESC;",
                (workspace_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": str(r["id"]),
                    "workspace_id": str(r["workspace_id"]),
                    "tool_name": r["tool_name"],
                    "arguments": r["arguments"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
