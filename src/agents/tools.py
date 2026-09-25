"""
Workspace Tools module.
Defines workspace-scoped tools using the @tool decorator with Pydantic validation,
audit logging, and workspace tenancy boundaries.
"""

from typing import Any
import requests
from pydantic import BaseModel, Field, field_validator
from langchain_core.tools import BaseTool, tool

from src.core.config import get_secret
from src.database import repository


# ==============================================================================
# Pydantic Schemas for Tool Arguments
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
        row = repository.save_task(
            workspace_id=workspace_id,
            title=validated.title,
            priority=validated.priority,
        )
        status = "SUCCESS"
        return f"Task '{validated.title}' successfully saved with priority '{validated.priority}' (Task ID: {row['id']})."
    except Exception as exc:
        status = "FAILED"
        return f"Failed to save task: {str(exc)}"
    finally:
        repository.log_tool_execution(
            workspace_id=workspace_id,
            tool_name="save_task",
            arguments={"title": title, "priority": priority},
            status=status,
        )


def send_discord_alert(message: str, workspace_id: str | None = None) -> str:
    """
    Posts an alert message to Discord webhook using DISCORD_WEBHOOK_URL.
    Logs execution to tool_logs audit table.
    """
    status = "FAILED"
    try:
        validated = SendDiscordAlertInput(message=message)
        webhook_url = get_secret("DISCORD_WEBHOOK_URL")

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
        repository.log_tool_execution(
            workspace_id=workspace_id,
            tool_name="send_discord_alert",
            arguments={"message": message},
            status=status,
        )


# ==============================================================================
# LangChain @tool Declarations & Factory
# ==============================================================================


@tool("save_task", args_schema=SaveTaskInput)
def save_task_tool(title: str, priority: str) -> str:
    """Save a new task with a title and priority ('low', 'medium', 'high') to the workspace task tracker."""
    return save_task(title=title, priority=priority, workspace_id="")


@tool("send_discord_alert", args_schema=SendDiscordAlertInput)
def send_discord_alert_tool(message: str) -> str:
    """Send a real-time notification or alert message to the Discord channel via webhook."""
    return send_discord_alert(message=message, workspace_id=None)


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
    def scoped_save_task_tool(title: str, priority: str) -> str:
        """Save a new task with a title and priority ('low', 'medium', 'high') to the workspace task tracker."""
        return save_task(title=title, priority=priority, workspace_id=workspace_id)

    @tool("send_discord_alert", args_schema=SendDiscordAlertInput)
    def scoped_send_discord_alert_tool(message: str) -> str:
        """Send a real-time notification or alert message to the Discord channel via webhook."""
        return send_discord_alert(message=message, workspace_id=workspace_id)

    return [scoped_save_task_tool, scoped_send_discord_alert_tool]


# Re-export dashboard query helpers for convenience
get_workspace_tasks = repository.get_workspace_tasks
get_tool_logs = repository.get_tool_logs
