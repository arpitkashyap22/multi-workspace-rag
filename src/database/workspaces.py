"""
Workspaces database repository module.
Handles workspace CRUD operations scoped by user_id.
"""

from typing import Any
from psycopg.rows import dict_row
from src.database.connection import get_db_connection


def get_user_workspaces(user_id: str) -> list[dict[str, Any]]:
    """Retrieve all workspaces belonging to a user."""
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, user_id, name, created_at FROM workspaces WHERE user_id = %s ORDER BY created_at ASC;",
                (user_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": str(r["id"]),
                    "user_id": r["user_id"],
                    "name": r["name"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]


def create_workspace(user_id: str, name: str) -> dict[str, Any]:
    """Create a new workspace for a user."""
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "INSERT INTO workspaces (user_id, name) VALUES (%s, %s) RETURNING id, user_id, name, created_at;",
                (user_id, name.strip()),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"Failed to create workspace '{name}': no row returned")
            return {
                "id": str(row["id"]),
                "user_id": row["user_id"],
                "name": row["name"],
                "created_at": row["created_at"],
            }


def delete_workspace(user_id: str, workspace_id: str) -> dict[str, Any] | None:
    """
    Deletes a workspace record strictly scoped to user_id.
    Because of ON DELETE CASCADE, foreign key tables (documents, tasks, tool_logs)
    are automatically cleaned up at the database level.
    """
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                DELETE FROM workspaces
                WHERE id = %s AND user_id = %s
                RETURNING id, user_id, name;
                """,
                (workspace_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": str(row["id"]),
                "user_id": str(row["user_id"]),
                "name": row["name"],
            }
