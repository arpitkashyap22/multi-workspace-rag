"""
Services package: object storage operations and RAG document intelligence pipeline.
"""

from src.services.storage import upload_file_to_blob, get_file_from_blob
from src.services.rag import (
    get_embeddings_model,
    get_text_splitter,
    get_embedding,
    get_embeddings_batch,
    chunk_text,
    format_chunks_as_readonly_blocks,
    retrieve_workspace_chunks,
    ingest_document,
    create_document_search_tool,
)

__all__ = [
    "upload_file_to_blob",
    "get_file_from_blob",
    "get_embeddings_model",
    "get_text_splitter",
    "get_embedding",
    "get_embeddings_batch",
    "chunk_text",
    "format_chunks_as_readonly_blocks",
    "retrieve_workspace_chunks",
    "ingest_document",
    "create_document_search_tool",
]
