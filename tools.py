"""
Workspace tools and LangChain integration for Document Assistant Agent.
Defines workspace-scoped tools using the @tool decorator for clarity and readability,
with Pydantic validation and audit logging to tool_logs.
"""

import os
import json
from typing import Any
import requests
import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from psycopg.rows import dict_row
from langchain_core.tools import BaseTool, tool

import db

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


# ==============================================================================
# Pydantic Schemas for Tool Arguments & Dashboard Records
# ==============================================================================


class SaveTaskInput(BaseModel):
    """Pydantic input schema for saving a task with title and priority."""

    title: str = Field(..., min_length=1, description="The title or clear description of the task.")
    priority: str = Field(..., description="Priority level of the task: 'low', 'medium', or 'high'.")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ("low", "medium", "high"):
            raise ValueError(f"Invalid priority '{v}'. Priority must be one of: 'low', 'medium', 'high'.")
        return clean


class SendDiscordAlertInput(BaseModel):
    """Pydantic input schema for sending an alert message to Discord."""

    message: str = Field(..., min_length=1, description="The alert message content to broadcast to Discord.")


class TaskRecord(BaseModel):
    """Pydantic model for a workspace task stored in workspace_tasks."""

    id: str
    workspace_id: str
    title: str
    priority: str
    created_at: Any

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class ToolLogRecord(BaseModel):
    """Pydantic model for an audit log record stored in tool_logs."""

    id: str
    workspace_id: str
    tool_name: str
    arguments: Any
    status: str
    created_at: Any

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


# ==============================================================================
# Audit Logging Helper
# ==============================================================================


def _log_tool_execution(
    workspace_id: str | None,
    tool_name: str,
    tool_args: dict[str, Any],
    status: str,
) -> None:
    """Records tool execution into tool_logs table with status 'SUCCESS' or 'FAILED'."""
    if not workspace_id:
        return

    try:
        with db.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tool_logs (workspace_id, tool_name, arguments, status)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (str(workspace_id), tool_name, json.dumps(tool_args), status),
                )
                conn.commit()
    except Exception as e:
        print(f"Warning: Failed to write to tool_logs: {e}")


# ==============================================================================
# Core Tool Actions
# ==============================================================================


def save_task(
    title: str,
    priority: str,
    workspace_id: str,
) -> str:
    """
    Inserts a task into workspace_tasks scoped strictly to workspace_id.
    Logs execution to tool_logs audit table.
    """
    if not workspace_id:
        raise ValueError("workspace_id is required to scope the task.")

    status = "FAILED"
    try:
        validated = SaveTaskInput(title=title, priority=priority)

        with db.get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO workspace_tasks (workspace_id, title, priority)
                    VALUES (%s, %s, %s)
                    RETURNING id, workspace_id, title, priority, created_at;
                    """,
                    (str(workspace_id), validated.title, validated.priority),
                )
                row = cur.fetchone()
                conn.commit()

        status = "SUCCESS"
        return f"Task '{validated.title}' successfully saved with priority '{validated.priority}' (Task ID: {row['id']})."
    except Exception as exc:
        status = "FAILED"
        return f"Failed to save task: {str(exc)}"
    finally:
        _log_tool_execution(workspace_id, "save_task", {"title": title, "priority": priority}, status)


def send_discord_alert(message: str, workspace_id: str | None = None) -> str:
    """
    Posts an alert message to Discord webhook using DISCORD_WEBHOOK_URL.
    Logs execution to tool_logs audit table.
    """
    status = "FAILED"
    try:
        validated = SendDiscordAlertInput(message=message)
        webhook_url = _get_secret("DISCORD_WEBHOOK_URL")

        payload = {"content": validated.message}
        response = requests.post(webhook_url, json=payload, timeout=10)

        if response.status_code not in (200, 204):
            raise RuntimeError(
                f"Discord webhook returned status code {response.status_code}: {response.text}"
            )

        status = "SUCCESS"
        return f"Discord alert successfully sent: '{validated.message}'."
    except Exception as exc:
        status = "FAILED"
        return f"Failed to send Discord alert: {str(exc)}"
    finally:
        _log_tool_execution(workspace_id, "send_discord_alert", {"message": message}, status)


# ==============================================================================
# LangChain @tool Declarations & Factory
# ==============================================================================


def get_workspace_tools(workspace_id: str) -> list[BaseTool]:
    """
    Creates LangChain BaseTool instances using the @tool decorator,
    with the target workspace_id bound directly into the execution closure.

    Args:
        workspace_id: The UUID of the current active workspace.

    Returns:
        list[BaseTool]: Clean LangChain tools defined via @tool.
    """

    @tool("save_task", args_schema=SaveTaskInput)
    def save_task_tool(title: str, priority: str) -> str:
        """Save a new task with a title and priority ('low', 'medium', 'high') to the workspace task tracker."""
        return save_task(title=title, priority=priority, workspace_id=workspace_id)

    @tool("send_discord_alert", args_schema=SendDiscordAlertInput)
    def send_discord_alert_tool(message: str) -> str:
        """Send a real-time notification or alert message to the Discord channel via webhook."""
        return send_discord_alert(message=message, workspace_id=workspace_id)

    return [save_task_tool, send_discord_alert_tool]


# ==============================================================================
# Dashboard Queries
# ==============================================================================


def get_workspace_tasks(workspace_id: str) -> list[TaskRecord]:
    """Retrieve all tasks for a workspace ordered by most recent, returning Pydantic models."""
    with db.get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, workspace_id, title, priority, created_at
                FROM workspace_tasks
                WHERE workspace_id = %s
                ORDER BY created_at DESC;
                """,
                (str(workspace_id),),
            )
            return [
                TaskRecord(
                    id=str(r["id"]),
                    workspace_id=str(r["workspace_id"]),
                    title=r["title"],
                    priority=r["priority"],
                    created_at=r["created_at"],
                )
                for r in cur.fetchall()
            ]


def get_tool_logs(workspace_id: str) -> list[ToolLogRecord]:
    """Retrieve audit logs for a workspace ordered by most recent, returning Pydantic models."""
    with db.get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, workspace_id, tool_name, arguments, status, created_at
                FROM tool_logs
                WHERE workspace_id = %s
                ORDER BY created_at DESC;
                """,
                (str(workspace_id),),
            )
            return [
                ToolLogRecord(
                    id=str(r["id"]),
                    workspace_id=str(r["workspace_id"]),
                    tool_name=r["tool_name"],
                    arguments=r["arguments"],
                    status=r["status"],
                    created_at=r["created_at"],
                )
                for r in cur.fetchall()
            ]
