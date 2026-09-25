"""
Services package: object storage operations and LangChain-powered RAG document intelligence pipeline.
"""

from src.services.storage import (
    upload_file_to_blob,
    get_file_from_blob,
    get_file_bytes_from_blob,
    delete_file_from_blob,
    delete_workspace_blobs,
)
from src.services.rag import (
    extract_text_from_pdf,
    extract_text_from_file,
    get_embeddings_model,
    get_text_splitter,
    get_vector_store,
    load_text_document,
    chunk_documents,
    format_documents_as_readonly_blocks,
    retrieve_workspace_chunks,
    ingest_document,
    delete_document,
    delete_workspace_pipeline,
)

__all__ = [
    "upload_file_to_blob",
    "get_file_from_blob",
    "get_file_bytes_from_blob",
    "delete_file_from_blob",
    "delete_workspace_blobs",
    "extract_text_from_pdf",
    "extract_text_from_file",
    "get_embeddings_model",
    "get_text_splitter",
    "get_vector_store",
    "load_text_document",
    "chunk_documents",
    "format_documents_as_readonly_blocks",
    "retrieve_workspace_chunks",
    "ingest_document",
    "delete_document",
    "delete_workspace_pipeline",
]
