"""
Foundational module for object storage operations using S3-compatible Neon Object Storage.
"""

import os
import boto3
from botocore.client import Config
import streamlit as st
from dotenv import load_dotenv

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


BUCKET_NAME = _get_secret("S3_BUCKET", "uploads")

s3_client = boto3.client(
    "s3",
    endpoint_url=_get_secret("AWS_ENDPOINT_URL_S3"),
    aws_access_key_id=_get_secret("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=_get_secret("AWS_SECRET_ACCESS_KEY"),
    region_name=_get_secret("AWS_REGION"),
    config=Config(s3={"addressing_style": "path"}),
)


def upload_file_to_blob(workspace_id: str, filename: str, file_bytes: bytes | str) -> str:
    """
    Uploads a file to Neon Object Storage at workspaces/{workspace_id}/{filename}.

    Args:
        workspace_id: The ID of the workspace.
        filename: The original name of the file.
        file_bytes: The file contents as bytes or string.

    Returns:
        The blob path in the bucket (e.g. 'workspaces/{workspace_id}/{filename}').
    """
    blob_path = f"workspaces/{workspace_id}/{filename}"
    if isinstance(file_bytes, str):
        file_bytes = file_bytes.encode("utf-8")

    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=blob_path,
        Body=file_bytes,
    )
    return blob_path


def get_file_from_blob(blob_path: str) -> str:
    """
    Downloads and returns the file content as a string.

    Args:
        blob_path: The path of the file in the bucket.

    Returns:
        The file content decoded as a UTF-8 string.
    """
    clean_path = blob_path.lstrip("/")
    response = s3_client.get_object(
        Bucket=BUCKET_NAME,
        Key=clean_path,
    )
    return response["Body"].read().decode("utf-8", errors="replace")
