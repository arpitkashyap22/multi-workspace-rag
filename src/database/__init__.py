"""
Database package for PostgreSQL connection, pgvector registration, and tenancy-isolated repositories.
"""

from src.database.connection import get_db_connection
from src.database.repository import (
    signup_user,
    login_user,
    create_workspace,
    get_user_workspaces,
    get_workspace_documents,
    save_document_metadata,
    get_workspace_tasks,
    get_tool_logs,
    log_tool_execution,
)

__all__ = [
    "get_db_connection",
    "signup_user",
    "login_user",
    "create_workspace",
    "get_user_workspaces",
    "get_workspace_documents",
    "save_document_metadata",
    "get_workspace_tasks",
    "get_tool_logs",
    "log_tool_execution",
]
