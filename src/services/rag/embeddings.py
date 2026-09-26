"""
LangChain Embeddings & Text Splitting module.
Manages Google Generative AI embeddings configuration and document segmentation.
"""

from typing import Any, Sequence
import streamlit as st
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.core.config import get_gemini_api_key


@st.cache_resource(show_spinner=False)
def get_embeddings_model() -> GoogleGenerativeAIEmbeddings:
    """
    Initializes and caches LangChain's GoogleGenerativeAIEmbeddings configured
    for 768-dimensional vectors matching the PostgreSQL pgvector schema.
    """
    api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError(
            "Gemini API key not found. Please set GEMINI_API_KEY in .streamlit/secrets.toml or as an environment variable."
        )
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=api_key,
        output_dimensionality=768,
    )


def get_text_splitter(
    chunk_size: int = 500, chunk_overlap: int = 50
) -> RecursiveCharacterTextSplitter:
    """Instantiates a LangChain RecursiveCharacterTextSplitter for document chunking."""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )


def load_text_document(
    text_content: str,
    filename: str,
    metadata: dict[str, Any] | None = None,
) -> Document:
    """
    Constructs a LangChain Document instance with unified tenancy metadata.
    """
    doc_metadata: dict[str, Any] = {"filename": filename}
    if metadata:
        doc_metadata.update(metadata)
    return Document(page_content=text_content, metadata=doc_metadata)


def chunk_documents(
    documents: Sequence[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[Document]:
    """Splits a sequence of LangChain Documents into chunk Documents."""
    splitter = get_text_splitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_documents(list(documents))
