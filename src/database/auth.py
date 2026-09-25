"""
Neon Auth REST API integration module.
Handles user registration, authentication, and initial workspace provisioning.
"""

from typing import Any
import requests
from src.core.config import get_neon_auth_base_url
from src.database.workspaces import create_workspace, get_user_workspaces


def _get_auth_url(subpath: str) -> str:
    """Constructs the Neon Auth REST endpoint URL."""
    base = get_neon_auth_base_url().rstrip("/")
    if base.endswith("/auth"):
        base = base[:-5]
    endpoint = subpath.lstrip("/")
    return f"{base}/auth/{endpoint}"


def signup_user(email: str, password: str) -> dict[str, Any]:
    """
    Register a new user via Neon Auth REST API and seed a default 'General' workspace.
    """
    url = _get_auth_url("sign-up/email")
    headers = {
        "Content-Type": "application/json",
        "Origin": "http://localhost:8501",
    }
    payload = {
        "email": email,
        "password": password,
        "name": email.split("@")[0],
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in (200, 201):
            data = response.json()
            user_info = data.get("user", {})
            user_id = user_info.get("id") or data.get("id")
            user_email = user_info.get("email") or email

            # Automatically seed default workspace named 'General'
            try:
                existing = get_user_workspaces(user_id)
                if not any(ws["name"] == "General" for ws in existing):
                    create_workspace(user_id=user_id, name="General")
            except Exception as ws_err:
                print(f"Warning: Failed to seed default workspace for user {user_id}: {ws_err}")

            return {
                "success": True,
                "user_id": user_id,
                "email": user_email,
            }
        else:
            error_msg = response.text
            try:
                err_json = response.json()
                error_msg = err_json.get("message") or err_json.get("code") or response.text
            except Exception:
                pass
            return {"success": False, "error": error_msg}
    except Exception as e:
        return {"success": False, "error": str(e)}


def login_user(email: str, password: str) -> dict[str, Any]:
    """Log in a user via Neon Auth REST API."""
    url = _get_auth_url("sign-in/email")
    headers = {
        "Content-Type": "application/json",
        "Origin": "http://localhost:8501",
    }
    payload = {
        "email": email,
        "password": password,
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in (200, 201):
            data = response.json()
            user_info = data.get("user", {})
            user_id = user_info.get("id") or data.get("id")
            user_email = user_info.get("email") or email
            return {
                "success": True,
                "user_id": user_id,
                "email": user_email,
            }
        else:
            error_msg = response.text
            try:
                err_json = response.json()
                error_msg = err_json.get("message") or err_json.get("code") or response.text
            except Exception:
                pass
            return {"success": False, "error": error_msg}
    except Exception as e:
        return {"success": False, "error": str(e)}
