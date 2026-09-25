"""
Unified Database Repository Facade.
Aggregates domain-specific repositories (auth, workspaces, documents, tasks, audit)
while maintaining backward-compatible access across the application.
"""

from src.database.auth import signup_user, login_user
from src.database.workspaces import get_user_workspaces, create_workspace
from src.database.documents import (
    get_workspace_documents,
    check_document_hash_exists,
    save_document_metadata,
    delete_document,
)
from src.database.tasks import save_task, get_workspace_tasks
from src.database.audit import log_tool_execution, get_tool_logs

__all__ = [
    "signup_user",
    "login_user",
    "get_user_workspaces",
    "create_workspace",
    "get_workspace_documents",
    "check_document_hash_exists",
    "save_document_metadata",
    "delete_document",
    "save_task",
    "get_workspace_tasks",
    "log_tool_execution",
    "get_tool_logs",
]
