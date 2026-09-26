"""
Conversations and Chat Messages database repository module.
Handles persistent multi-turn chat threads and message history scoped by workspace_id.
"""

from typing import Any
import json
import streamlit as st
from psycopg.rows import dict_row
from src.database.connection import get_db_connection


@st.cache_resource(show_spinner=False)
def init_chat_tables() -> None:
    """Creates conversations and chat_messages tables if they do not exist (cached once)."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                    title TEXT NOT NULL DEFAULT 'New Chat',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources JSONB DEFAULT '[]'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_conversations_workspace_id ON conversations(workspace_id);
                CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id ON chat_messages(conversation_id);
                """
            )
            conn.commit()


@st.cache_data(ttl="30s", max_entries=50, show_spinner=False)
def get_workspace_conversations(workspace_id: str) -> list[dict[str, Any]]:
    """Retrieve all conversation threads belonging to a workspace, ordered by most recently updated."""
    init_chat_tables()
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, workspace_id, title, created_at, updated_at
                FROM conversations
                WHERE workspace_id = %s
                ORDER BY updated_at DESC;
                """,
                (workspace_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": str(r["id"]),
                    "workspace_id": str(r["workspace_id"]),
                    "title": r["title"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                }
                for r in rows
            ]


def create_conversation(workspace_id: str, title: str = "New Chat") -> dict[str, Any]:
    """Create a new conversation thread in a workspace."""
    init_chat_tables()
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO conversations (workspace_id, title)
                VALUES (%s, %s)
                RETURNING id, workspace_id, title, created_at, updated_at;
                """,
                (workspace_id, title.strip() or "New Chat"),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"Failed to create conversation for workspace {workspace_id}")

            try:
                get_workspace_conversations.clear()
            except Exception:
                pass

            return {
                "id": str(row["id"]),
                "workspace_id": str(row["workspace_id"]),
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }


def get_conversation(conversation_id: str) -> dict[str, Any] | None:
    """Retrieve a single conversation by its UUID."""
    init_chat_tables()
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, workspace_id, title, created_at, updated_at
                FROM conversations
                WHERE id = %s;
                """,
                (conversation_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": str(row["id"]),
                "workspace_id": str(row["workspace_id"]),
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }


def update_conversation_title(conversation_id: str, title: str) -> None:
    """Update conversation title (e.g. summarized from first user question)."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE conversations
                SET title = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
                """,
                (title.strip()[:60] or "New Chat", conversation_id),
            )
            conn.commit()
            try:
                get_workspace_conversations.clear()
            except Exception:
                pass


def delete_conversation(conversation_id: str, workspace_id: str) -> bool:
    """Delete a conversation thread scoped by workspace_id."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM conversations
                WHERE id = %s AND workspace_id = %s;
                """,
                (conversation_id, workspace_id),
            )
            deleted = cur.rowcount > 0
            conn.commit()
            try:
                get_workspace_conversations.clear()
            except Exception:
                pass
            try:
                get_conversation_messages.clear()
            except Exception:
                pass
            return deleted


@st.cache_data(ttl="60s", max_entries=100, show_spinner=False)
def get_conversation_messages(conversation_id: str) -> list[dict[str, Any]]:
    """Retrieve all messages in a conversation ordered chronologically (cached for fast reruns)."""
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, conversation_id, role, content, sources, created_at
                FROM chat_messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC;
                """,
                (conversation_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": str(r["id"]),
                    "conversation_id": str(r["conversation_id"]),
                    "role": r["role"],
                    "content": r["content"],
                    "sources": r["sources"] if isinstance(r["sources"], list) else json.loads(r["sources"] or "[]"),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]


def save_chat_message(
    conversation_id: str,
    role: str,
    content: str,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    """
    Save a message (user or assistant) to chat_messages and update the conversation's updated_at timestamp.
    Invalidates conversation and message caches.
    """
    sources_json = json.dumps(sources or [])
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO chat_messages (conversation_id, role, content, sources)
                VALUES (%s, %s, %s, %s::jsonb)
                RETURNING id, conversation_id, role, content, sources, created_at;
                """,
                (conversation_id, role, content, sources_json),
            )
            msg_row = cur.fetchone()
            if not msg_row:
                raise RuntimeError("Failed to insert chat message")

            # Touch conversation updated_at
            cur.execute(
                """
                UPDATE conversations
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
                """,
                (conversation_id,),
            )
            conn.commit()

            try:
                get_workspace_conversations.clear()
            except Exception:
                pass

            try:
                get_conversation_messages.clear()
            except Exception:
                pass

            return {
                "id": str(msg_row["id"]),
                "conversation_id": str(msg_row["conversation_id"]),
                "role": msg_row["role"],
                "content": msg_row["content"],
                "sources": sources or [],
                "created_at": msg_row["created_at"],
            }


def clear_conversation_messages(conversation_id: str) -> int:
    """Clear all messages from a conversation."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM chat_messages WHERE conversation_id = %s;",
                (conversation_id,),
            )
            count = cur.rowcount
            conn.commit()
            return count
