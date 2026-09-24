"""
Foundational database module using psycopg, pgvector, and Neon Auth REST API.
Enforces strict multi-tenant workspace isolation.
"""

import os
import requests
import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def _get_secret(key: str, default: str | None = None) -> str:
    """Retrieve secret from st.secrets if available, falling back to os.environ."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    val = os.getenv(key, default)
    if val is None:
        raise KeyError(f"Secret or environment variable '{key}' not found.")
    return val


def get_db_connection() -> psycopg.Connection:
    """
    Connect to PostgreSQL using psycopg and register pgvector extension.
    """
    db_url = _get_secret("DATABASE_URL")
    conn = psycopg.connect(db_url)
    register_vector(conn)
    return conn


def _get_auth_url(subpath: str) -> str:
    """
    Constructs the Neon Auth REST endpoint URL.
    Handles whether NEON_AUTH_BASE_URL already contains '/auth' or not.
    """
    base = _get_secret("NEON_AUTH_BASE_URL").rstrip("/")
    if base.endswith("/auth"):
        base = base[:-5]
    endpoint = subpath.lstrip("/")
    return f"{base}/auth/{endpoint}"


def signup_user(email: str, password: str) -> dict:
    """
    Register a new user via Neon Auth REST API and seed a default 'General' workspace.

    Args:
        email: User email address.
        password: User password.

    Returns:
        dict: {"success": True, "user_id": ..., "email": ...} on success,
              or {"success": False, "error": ...} on failure.
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
                existing_workspaces = get_user_workspaces(user_id)
                if not any(ws["name"] == "General" for ws in existing_workspaces):
                    create_workspace(user_id=user_id, name="General")
            except Exception as ws_err:
                # Log or ensure workspace creation attempt was recorded
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
            return {
                "success": False,
                "error": error_msg,
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def login_user(email: str, password: str) -> dict:
    """
    Log in a user via Neon Auth REST API.

    Args:
        email: User email address.
        password: User password.

    Returns:
        dict: {"success": True, "user_id": ..., "email": ...} on success,
              or {"success": False, "error": ...} on failure.
    """
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
            return {
                "success": False,
                "error": error_msg,
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def get_user_workspaces(user_id: str) -> list[dict]:
    """
    Retrieve all workspaces belonging to a user using a parameterized SQL query.

    Args:
        user_id: The unique identifier of the user.

    Returns:
        list[dict]: List of workspace records with id, user_id, name, and created_at.
    """
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


def create_workspace(user_id: str, name: str) -> dict:
    """
    Create a new workspace for a user using a parameterized SQL query.

    Args:
        user_id: The unique identifier of the user.
        name: The name of the workspace.

    Returns:
        dict: The newly created workspace record.
    """
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


def get_workspace_documents(workspace_id: str) -> list[dict]:
    """
    Retrieve documents belonging to a workspace using a parameterized query.
    Selects id, filename, blob_path, and created_at from documents.

    Args:
        workspace_id: The UUID of the workspace.

    Returns:
        list[dict]: List of documents in the workspace.
    """
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


# Alias matching alternative naming
aget_workspace_documents = get_workspace_documents
