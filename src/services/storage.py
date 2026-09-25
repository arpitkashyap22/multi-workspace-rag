"""
Object Storage service for S3-compatible Neon Object Storage.
Stores original raw document files scoped to workspaces/{workspace_id}/{filename}.
"""

from typing import Any
import boto3
from botocore.client import Config
from src.core.config import get_secret


def _get_s3_client() -> tuple[Any, str]:
    """Instantiate S3 client and fetch bucket name from config."""
    bucket_name = get_secret("S3_BUCKET", default="uploads")
    client = boto3.client(
        "s3",
        endpoint_url=get_secret("AWS_ENDPOINT_URL_S3"),
        aws_access_key_id=get_secret("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=get_secret("AWS_SECRET_ACCESS_KEY"),
        region_name=get_secret("AWS_REGION", default="us-east-1"),
        config=Config(s3={"addressing_style": "path"}),
    )
    return client, bucket_name


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
    client, bucket_name = _get_s3_client()
    blob_path = f"workspaces/{workspace_id}/{filename}"
    if isinstance(file_bytes, str):
        file_bytes = file_bytes.encode("utf-8")

    client.put_object(
        Bucket=bucket_name,
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
    client, bucket_name = _get_s3_client()
    clean_path = blob_path.lstrip("/")
    response = client.get_object(
        Bucket=bucket_name,
        Key=clean_path,
    )
    return response["Body"].read().decode("utf-8", errors="replace")
