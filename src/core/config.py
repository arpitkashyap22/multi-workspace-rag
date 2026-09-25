"""
Configuration module.
Provides centralized access to application secrets, environment variables,
and default model/service parameters.
"""

import os
from typing import Any
from dotenv import load_dotenv
import streamlit as st

load_dotenv()


def get_secret(key: str, default: str | None = None) -> str:
    """
    Retrieve a secret from st.secrets if available, falling back to os.environ.
    Raises KeyError if key is not found and no default is provided.
    """
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass

    val = os.getenv(key, default)
    if val is None:
        raise KeyError(f"Configuration key '{key}' not found in st.secrets or environment variables.")
    return val


def get_gemini_api_key() -> str | None:
    """Retrieve Gemini API key from secrets or environment."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return str(st.secrets["GEMINI_API_KEY"])
        if "GOOGLE_API_KEY" in st.secrets:
            return str(st.secrets["GOOGLE_API_KEY"])
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def get_chat_model() -> str:
    """Retrieve chat model identifier, defaulting to gemini-3.1-flash-lite."""
    try:
        if "GEMINI_CHAT_MODEL" in st.secrets:
            return str(st.secrets["GEMINI_CHAT_MODEL"])
    except Exception:
        pass
    return os.getenv("GEMINI_CHAT_MODEL", "gemini-3.1-flash-lite")


def get_embedding_model() -> str:
    """Retrieve embedding model identifier, defaulting to models/text-embedding-004."""
    try:
        if "GEMINI_EMBEDDING_MODEL" in st.secrets:
            return str(st.secrets["GEMINI_EMBEDDING_MODEL"])
    except Exception:
        pass
    return os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")


def get_database_url() -> str:
    """Retrieve PostgreSQL connection string."""
    return get_secret("DATABASE_URL")


def get_neon_auth_base_url() -> str:
    """Retrieve Neon Auth REST API base URL."""
    return get_secret("NEON_AUTH_BASE_URL")


def get_storage_config() -> dict[str, Any]:
    """Retrieve S3-compatible Neon Object Storage credentials."""
    return {
        "endpoint_url": get_secret("STORAGE_ENDPOINT_URL"),
        "aws_access_key_id": get_secret("STORAGE_ACCESS_KEY_ID"),
        "aws_secret_access_key": get_secret("STORAGE_SECRET_ACCESS_KEY"),
        "bucket_name": get_secret("STORAGE_BUCKET_NAME"),
        "region_name": get_secret("STORAGE_REGION", default="us-east-1"),
    }
