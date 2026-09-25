"""
Core module: configuration, environment settings, and domain Pydantic models.
"""

from src.core.config import (
    get_secret,
    get_gemini_api_key,
    get_chat_model,
    get_embedding_model,
    get_database_url,
    get_neon_auth_base_url,
    get_storage_config,
)
from src.core.models import (
    RetrievedChunk,
    RetrievedContext,
    IngestionResult,
    AgentToolEvent,
    AgentResponse,
    UserSession,
    Workspace,
    WorkspaceTask,
    ToolLog,
)

__all__ = [
    "get_secret",
    "get_gemini_api_key",
    "get_chat_model",
    "get_embedding_model",
    "get_database_url",
    "get_neon_auth_base_url",
    "get_storage_config",
    "RetrievedChunk",
    "RetrievedContext",
    "IngestionResult",
    "AgentToolEvent",
    "AgentResponse",
    "UserSession",
    "Workspace",
    "WorkspaceTask",
    "ToolLog",
]
