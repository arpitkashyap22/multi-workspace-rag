"""
Documents database repository module.
Handles document record metadata and idempotency checks strictly scoped by workspace_id.
"""

from typing import Any
import streamlit as st
from psycopg.rows import dict_row
from src.database.connection import get_db_connection


@st.cache_data(ttl="30s", max_entries=50, show_spinner=False)
def get_workspace_documents(workspace_id: str) -> list[dict[str, Any]]:
    """Retrieve all document records for a workspace (cached for rapid tab rendering)."""
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, filename, blob_path, created_at FROM documents WHERE workspace_id = %s ORDER BY created_at DESC;",
                (workspace_id,),
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
                (workspace_id, file_hash),
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
                (workspace_id, filename, file_hash, blob_path),
            )
            doc_row = cur.fetchone()
            if not doc_row:
                raise RuntimeError(f"Failed to save document metadata for '{filename}': no row returned")

            # Clear cached document list
            try:
                get_workspace_documents.clear()
            except Exception:
                pass

            return str(doc_row[0])


def delete_document(workspace_id: str, document_id: str) -> dict[str, Any] | None:
    """
    Delete a document record scoped strictly to workspace_id.
    Returns the deleted document metadata (id, filename, blob_path) if found, else None.
    """
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                DELETE FROM documents
                WHERE id = %s AND workspace_id = %s
                RETURNING id, filename, blob_path;
                """,
                (document_id, workspace_id),
            )
            deleted = cur.fetchone()
            if not deleted:
                return None

            # Also ensure any lingering legacy document_chunks are cleaned up
            cur.execute(
                "DELETE FROM document_chunks WHERE document_id = %s AND workspace_id = %s;",
                (document_id, workspace_id),
            )

            # Clear cached document list
            try:
                get_workspace_documents.clear()
            except Exception:
                pass

            return {
                "id": str(deleted["id"]),
                "filename": deleted["filename"],
                "blob_path": deleted["blob_path"],
            }
