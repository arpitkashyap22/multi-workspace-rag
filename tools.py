"""
Tool execution and Gemini function calling module for multi-workspace document assistant.
Supports task persistence in PostgreSQL, Discord webhook alerts, Pydantic validation,
and auditable execution logging to tool_logs.
"""

import os
import json
from typing import Any
import requests
import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, ValidationError
from google.genai import types
from psycopg.rows import dict_row

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


# ==========================================
# Pydantic Input Schemas
# ==========================================


class SaveTaskInput(BaseModel):
    """Schema for saving a task with title and priority."""

    title: str = Field(..., min_length=1, description="The title or description of the task.")
    priority: str = Field(..., description="Priority level of the task: 'low', 'medium', or 'high'.")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ("low", "medium", "high"):
            raise ValueError(f"Invalid priority '{v}'. Priority must be one of: 'low', 'medium', 'high'.")
        return clean


class SendDiscordAlertInput(BaseModel):
    """Schema for sending an alert to Discord."""

    message: str = Field(..., min_length=1, description="The alert message content to send to Discord.")


# ==========================================
# Tool Implementations
# ==========================================


def save_task(
    title: str,
    priority: str,
    workspace_id: str | None = None,
) -> str:
    """
    Inserts a record into workspace_tasks scoped to workspace_id.
    Supports:
      - save_task(title="...", priority="high", workspace_id="...")
      - save_task(title, priority, workspace_id=...)
      - save_task(workspace_id, title, priority)

    Args:
        title: Task title or description
        priority: Priority ('low', 'medium', 'high')
        workspace_id: Workspace UUID string

    Returns:
        str: Status message with created task details.
    """
    # Detect if invoked positionally as save_task(workspace_id, title, priority)
    if workspace_id and workspace_id.strip().lower() in ("low", "medium", "high"):
        actual_ws = title
        actual_title = priority
        actual_priority = workspace_id
    else:
        actual_ws = workspace_id
        actual_title = title
        actual_priority = priority

    if not actual_ws:
        raise ValueError("workspace_id is required to scope the task.")

    # Validate with Pydantic
    validated = SaveTaskInput(title=actual_title, priority=actual_priority)

    with db.get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO workspace_tasks (workspace_id, title, priority)
                VALUES (%s, %s, %s)
                RETURNING id, workspace_id, title, priority, created_at;
                """,
                (str(actual_ws), validated.title, validated.priority),
            )
            row = cur.fetchone()
            conn.commit()

    return f"Task '{validated.title}' successfully saved with priority '{validated.priority}' (Task ID: {row['id']})."


def send_discord_alert(message: str) -> str:
    """
    Posts an alert message to Discord webhook using DISCORD_WEBHOOK_URL.

    Args:
        message: The message content to send.

    Returns:
        str: Clean confirmation message.
    """
    validated = SendDiscordAlertInput(message=message)
    webhook_url = _get_secret("DISCORD_WEBHOOK_URL")

    payload = {"content": validated.message}
    response = requests.post(webhook_url, json=payload, timeout=10)

    if response.status_code not in (200, 204):
        raise RuntimeError(
            f"Discord webhook failed with status code {response.status_code}: {response.text}"
        )

    return f"Discord alert successfully sent: '{validated.message}'."


# ==========================================
# Tool Execution & Audit Logging
# ==========================================


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


def execute_tool(workspace_id: str, tool_name: str, tool_args: Any) -> str:
    """
    Executes a tool call requested by Gemini with safety and logging:
    1. Validates arguments using Pydantic.
    2. Runs inside a try/except block (no crash on runtime failure).
    3. Records execution in tool_logs with status 'SUCCESS' or 'FAILED'.
    4. Returns a clean string message to feed back into the model.

    Args:
        workspace_id: The UUID of the active workspace.
        tool_name: Name of the tool to execute ('save_task' or 'send_discord_alert').
        tool_args: Tool arguments (dict or JSON string).

    Returns:
        str: Output message for the model.
    """
    # Parse arguments if string
    if isinstance(tool_args, str):
        try:
            tool_args = json.loads(tool_args)
        except Exception:
            tool_args = {"raw": tool_args}

    if not isinstance(tool_args, dict):
        tool_args = {}

    status = "FAILED"
    result_message = ""

    try:
        if tool_name == "save_task":
            validated_task = SaveTaskInput(**tool_args)
            result_message = save_task(
                title=validated_task.title,
                priority=validated_task.priority,
                workspace_id=workspace_id,
            )
            status = "SUCCESS"

        elif tool_name == "send_discord_alert":
            validated_alert = SendDiscordAlertInput(**tool_args)
            result_message = send_discord_alert(message=validated_alert.message)
            status = "SUCCESS"

        else:
            raise ValueError(
                f"Unknown tool '{tool_name}'. Available tools: 'save_task', 'send_discord_alert'."
            )

    except ValidationError as val_err:
        status = "FAILED"
        err_details = "; ".join([f"{e['loc'][0]}: {e['msg']}" for e in val_err.errors()])
        result_message = f"Tool '{tool_name}' failed input validation: {err_details}"

    except Exception as exc:
        status = "FAILED"
        result_message = f"Tool '{tool_name}' execution failed: {str(exc)}"

    finally:
        _log_tool_execution(workspace_id, tool_name, tool_args, status)

    return result_message


# ==========================================
# Dashboard Queries
# ==========================================


def get_workspace_tasks(workspace_id: str) -> list[dict]:
    """Retrieve all tasks for a workspace ordered by most recent."""
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
                {
                    "id": str(r["id"]),
                    "workspace_id": str(r["workspace_id"]),
                    "title": r["title"],
                    "priority": r["priority"],
                    "created_at": r["created_at"],
                }
                for r in cur.fetchall()
            ]


def get_tool_logs(workspace_id: str) -> list[dict]:
    """Retrieve execution logs for a workspace ordered by most recent."""
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
                {
                    "id": str(r["id"]),
                    "workspace_id": str(r["workspace_id"]),
                    "tool_name": r["tool_name"],
                    "arguments": r["arguments"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                }
                for r in cur.fetchall()
            ]


# ==========================================
# Gemini Function Declarations & Tool Export
# ==========================================

save_task_declaration = types.FunctionDeclaration(
    name="save_task",
    description="Save a new task with a title and priority level to the workspace task tracker.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "title": types.Schema(
                type=types.Type.STRING,
                description="The clear description or title of the action item or task to save.",
            ),
            "priority": types.Schema(
                type=types.Type.STRING,
                description="Priority level of the task. Allowed values: 'low', 'medium', 'high'.",
                enum=["low", "medium", "high"],
            ),
        },
        required=["title", "priority"],
    ),
)

send_discord_alert_declaration = types.FunctionDeclaration(
    name="send_discord_alert",
    description="Send a real-time notification or alert message to the Discord channel via webhook.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "message": types.Schema(
                type=types.Type.STRING,
                description="The content of the notification or alert message to post to Discord.",
            ),
        },
        required=["message"],
    ),
)

gemini_function_declarations = [save_task_declaration, send_discord_alert_declaration]
gemini_tool = types.Tool(function_declarations=gemini_function_declarations)
tools = [gemini_tool]
