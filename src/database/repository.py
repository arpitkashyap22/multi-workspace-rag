"""
Unified Database Repository Facade.
Aggregates domain-specific repositories (auth, workspaces, documents, tasks, audit)
while maintaining backward-compatible access across the application.
"""

from src.database.auth import signup_user, login_user
from src.database.workspaces import (
    get_user_workspaces,
    create_workspace,
    delete_workspace,
)
from src.database.documents import (
    get_workspace_documents,
    check_document_hash_exists,
    save_document_metadata,
    delete_document,
)
from src.database.tasks import save_task, get_workspace_tasks
from src.database.audit import log_tool_execution, get_tool_logs
from src.database.conversations import (
    get_workspace_conversations,
    create_conversation,
    get_conversation,
    update_conversation_title,
    delete_conversation,
    get_conversation_messages,
    save_chat_message,
    clear_conversation_messages,
)

__all__ = [
    "signup_user",
    "login_user",
    "get_user_workspaces",
    "create_workspace",
    "delete_workspace",
    "get_workspace_documents",
    "check_document_hash_exists",
    "save_document_metadata",
    "delete_document",
    "save_task",
    "get_workspace_tasks",
    "log_tool_execution",
    "get_tool_logs",
    "get_workspace_conversations",
    "create_conversation",
    "get_conversation",
    "update_conversation_title",
    "delete_conversation",
    "get_conversation_messages",
    "save_chat_message",
    "clear_conversation_messages",
]
