"""
Database Repository module.
Enforces strict multi-tenant workspace isolation at the SQL query level:
All operations filter or insert with `workspace_id = %s`.
"""

import json
from typing import Any
import requests
from psycopg.rows import dict_row
from src.database.connection import get_db_connection
from src.core.config import get_neon_auth_base_url


def _get_auth_url(subpath: str) -> str:
    """Constructs the Neon Auth REST endpoint URL."""
    base = get_neon_auth_base_url().rstrip("/")
    if base.endswith("/auth"):
        base = base[:-5]
    endpoint = subpath.lstrip("/")
    return f"{base}/auth/{endpoint}"


# ==============================================================================
# Auth & Workspaces
# ==============================================================================


def signup_user(email: str, password: str) -> dict[str, Any]:
    """
    Register a new user via Neon Auth REST API and seed a default 'General' workspace.
    """
    url = _get_auth_url("sign-up/email")
    headers = {
        "Content-Type": "application/json",
        "Origin": "http://localhost:8501",
    }
    payload = {
        "email": email,
        "password": password,
        "name": email.split("@")[0],
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in (200, 201):
            data = response.json()
            user_info = data.get("user", {})
            user_id = user_info.get("id") or data.get("id")
            user_email = user_info.get("email") or email

            # Automatically seed default workspace named 'General'
            try:
                existing = get_user_workspaces(user_id)
                if not any(ws["name"] == "General" for ws in existing):
                    create_workspace(user_id=user_id, name="General")
            except Exception as ws_err:
                print(f"Warning: Failed to seed default workspace for user {user_id}: {ws_err}")

            return {
                "success": True,
                "user_id": user_id,
                "email": user_email,
            }
        else:
            error_msg = response.text
            try:
                err_json = response.json()
                error_msg = err_json.get("message") or err_json.get("code") or response.text
            except Exception:
                pass
            return {"success": False, "error": error_msg}
    except Exception as e:
        return {"success": False, "error": str(e)}


def login_user(email: str, password: str) -> dict[str, Any]:
    """Log in a user via Neon Auth REST API."""
    url = _get_auth_url("sign-in/email")
    headers = {
        "Content-Type": "application/json",
        "Origin": "http://localhost:8501",
    }
    payload = {
        "email": email,
        "password": password,
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in (200, 201):
            data = response.json()
            user_info = data.get("user", {})
            user_id = user_info.get("id") or data.get("id")
            user_email = user_info.get("email") or email
            return {
                "success": True,
                "user_id": user_id,
                "email": user_email,
            }
        else:
            error_msg = response.text
            try:
                err_json = response.json()
                error_msg = err_json.get("message") or err_json.get("code") or response.text
            except Exception:
                pass
            return {"success": False, "error": error_msg}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_user_workspaces(user_id: str) -> list[dict[str, Any]]:
    """Retrieve all workspaces belonging to a user."""
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, user_id, name, created_at FROM workspaces WHERE user_id = %s ORDER BY created_at ASC;",
                (str(user_id),),
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
                (str(user_id), name.strip()),
            )
            row = cur.fetchone()
            return {
                "id": str(row["id"]),
                "user_id": row["user_id"],
                "name": row["name"],
                "created_at": row["created_at"],
            }


# ==============================================================================
# Documents & Vector Chunks (Tenancy Enforced)
# ==============================================================================


def get_workspace_documents(workspace_id: str) -> list[dict[str, Any]]:
    """Retrieve all document records for a workspace."""
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, filename, blob_path, created_at FROM documents WHERE workspace_id = %s ORDER BY created_at DESC;",
                (str(workspace_id),),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": str(r["id"]),
                    "filename": r["filename"],
                    "blob_path": r["blob_path"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]


def check_document_hash_exists(workspace_id: str, file_hash: str) -> dict[str, Any] | None:
    """Check if a file with the given SHA-256 hash already exists in this workspace."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, filename, blob_path, created_at
                FROM documents
                WHERE workspace_id = %s AND file_hash = %s
                LIMIT 1;
                """,
                (str(workspace_id), file_hash),
            )
            row = cur.fetchone()
            if row:
                return {
                    "id": str(row[0]),
                    "filename": row[1],
                    "blob_path": row[2],
                    "created_at": row[3],
                }
            return None


def save_document_metadata(
    workspace_id: str,
    filename: str,
    file_hash: str,
    blob_path: str,
) -> str:
    """Insert document metadata and return generated UUID."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (workspace_id, filename, file_hash, blob_path)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (str(workspace_id), filename, file_hash, blob_path),
            )
            doc_row = cur.fetchone()
            return str(doc_row[0])


def save_chunk(
    workspace_id: str,
    document_id: str,
    content: str,
    metadata: dict[str, Any],
    embedding: list[float],
) -> None:
    """Insert a single text chunk with vector embedding into document_chunks."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO document_chunks (workspace_id, document_id, content, metadata, embedding)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (str(workspace_id), str(document_id), content, json.dumps(metadata), embedding),
            )


def search_chunks(
    workspace_id: str,
    query_embedding: list[float],
    limit: int = 4,
) -> list[tuple[str, str | None]]:
    """
    Search document_chunks using pgvector cosine distance `<=>`.
    Strictly isolated with `WHERE workspace_id = %s`.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT content, metadata->>'filename'
                FROM document_chunks
                WHERE workspace_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
                (str(workspace_id), query_embedding, limit),
            )
            return cur.fetchall()


# ==============================================================================
# Tasks & Tool Audit Logs
# ==============================================================================


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
                (str(workspace_id), title.strip(), priority.lower()),
            )
            row = cur.fetchone()
            return {
                "id": str(row["id"]),
                "workspace_id": str(row["workspace_id"]),
                "title": row["title"],
                "priority": row["priority"],
                "created_at": row["created_at"],
            }


def get_workspace_tasks(workspace_id: str) -> list[dict[str, Any]]:
    """Retrieve all tasks belonging to the active workspace."""
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, workspace_id, title, priority, created_at FROM workspace_tasks WHERE workspace_id = %s ORDER BY created_at DESC;",
                (str(workspace_id),),
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
                    (str(workspace_id), tool_name, json.dumps(arguments), status),
                )
    except Exception as e:
        print(f"Warning: Failed to write to tool_logs: {e}")


def get_tool_logs(workspace_id: str) -> list[dict[str, Any]]:
    """Retrieve tool execution logs for the active workspace."""
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, workspace_id, tool_name, arguments, status, created_at FROM tool_logs WHERE workspace_id = %s ORDER BY created_at DESC;",
                (str(workspace_id),),
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
