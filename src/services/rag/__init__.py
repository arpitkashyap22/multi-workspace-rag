"""
RAG Service package.
Provides modular components for parsing, embeddings, vector storage,
context sanitization, and end-to-end ingestion/retrieval pipelines.
"""

from src.services.rag.parser import extract_text_from_pdf, extract_text_from_file
from src.services.rag.embeddings import (
    get_embeddings_model,
    get_text_splitter,
    load_text_document,
    chunk_documents,
)
from src.services.rag.vector_store import get_vector_store
from src.services.rag.context_builder import format_documents_as_readonly_blocks
from src.services.rag.pipeline import ingest_document, retrieve_workspace_chunks

__all__ = [
    "extract_text_from_pdf",
    "extract_text_from_file",
    "get_embeddings_model",
    "get_text_splitter",
    "load_text_document",
    "chunk_documents",
    "get_vector_store",
    "format_documents_as_readonly_blocks",
    "ingest_document",
    "retrieve_workspace_chunks",
]
