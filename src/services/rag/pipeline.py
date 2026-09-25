"""
RAG Ingestion and Semantic Retrieval Pipeline module.
Coordinates text parsing, idempotency hashing, object storage upload,
vector embedding, and multi-tenant similarity retrieval.
"""

import hashlib
from typing import Any
from langchain_core.documents import Document
from src.core.models import IngestionResult, RetrievedContext
from src.database.documents import (
    check_document_hash_exists,
    save_document_metadata,
    delete_document as db_delete_document,
)
from src.database.workspaces import delete_workspace as db_delete_workspace
from src.services.storage import (
    upload_file_to_blob,
    delete_file_from_blob,
    delete_workspace_blobs,
)
from src.services.rag.parser import extract_text_from_file
from src.services.rag.embeddings import (
    load_text_document,
    chunk_documents,
)
from src.services.rag.vector_store import (
    get_vector_store,
    delete_document_embeddings,
    delete_workspace_embeddings,
)
from src.services.rag.context_builder import format_documents_as_readonly_blocks


def ingest_document(
    workspace_id: str,
    filename: str,
    text_content: str | None = None,
    file_bytes: bytes | None = None,
) -> IngestionResult:
    """
    Ingests a document (.txt, .md, or .pdf) into the given workspace with strict tenancy boundaries:
    1. Extracts text from file_bytes or uses text_content.
    2. Calculates SHA-256 hash of extracted text for idempotency.
    3. Checks if (workspace_id, file_hash) exists in documents. Returns early if already present.
    4. Uploads raw file_bytes to Neon Object Storage via storage.upload_file_to_blob.
    5. Inserts document record into documents table with blob_path.
    6. Creates LangChain Document with tenancy metadata (workspace_id, document_id, filename).
    7. Splits document using RecursiveCharacterTextSplitter into chunks.
    8. Stores vectors in PostgreSQL using LangChain's PGVector with psycopg.
    """
    if file_bytes is None:
        if not text_content or not text_content.strip():
            raise ValueError(f"No extractable text or file content provided for '{filename}'.")
        file_bytes = text_content.encode("utf-8")

    if not text_content:
        text_content = extract_text_from_file(filename, file_bytes)

    if not text_content or not text_content.strip():
        raise ValueError(f"No extractable text found in '{filename}'.")


    # 1. Calculate SHA-256 hash of text_content for idempotency
    file_hash = hashlib.sha256(text_content.encode("utf-8")).hexdigest()

    # 2. Check if (workspace_id, file_hash) already exists in this workspace
    existing = check_document_hash_exists(workspace_id, file_hash)
    if existing:
        return IngestionResult(
            already_exists=True,
            doc_id=existing["id"],
            filename=existing["filename"],
            chunk_count=0,
            message=f"Document '{filename}' with hash {file_hash[:8]}... already exists in workspace.",
        )

    # 3. Upload to Neon Object Storage via storage.upload_file_to_blob
    blob_path = upload_file_to_blob(workspace_id, filename, file_bytes)

    # 4. Insert document record into documents table
    document_id = save_document_metadata(
        workspace_id=workspace_id,
        filename=filename,
        file_hash=file_hash,
        blob_path=blob_path,
    )

    # 5. Create LangChain Document with tenancy metadata
    raw_doc = load_text_document(
        text_content=text_content,
        filename=filename,
        metadata={
            "workspace_id": workspace_id,
            "document_id": document_id,
        },
    )

    # 6. Split document into chunks
    chunk_docs = chunk_documents([raw_doc], chunk_size=500, chunk_overlap=50)

    # Tag each chunk with its index in metadata
    for idx, chunk_doc in enumerate(chunk_docs):
        chunk_doc.metadata["chunk_index"] = idx

    # 7. Ingest directly via LangChain PGVector (handles embeddings and psycopg DB insertion automatically)
    if chunk_docs:
        vectorstore = get_vector_store()
        vectorstore.add_documents(chunk_docs)

    return IngestionResult(
        already_exists=False,
        doc_id=document_id,
        filename=filename,
        chunk_count=len(chunk_docs),
        message=f"Successfully ingested '{filename}' ({len(chunk_docs)} chunks) via LangChain PGVector.",
    )


def retrieve_workspace_chunks(
    workspace_id: str,
    query: str,
    limit: int = 4,
) -> RetrievedContext:
    """
    Retrieves the most semantically relevant chunks for a query within a workspace
    using LangChain's PGVector store:
    1. Executes vectorstore.similarity_search_with_score with tenant metadata filter.
       LangChain PGVector automatically embeds the query and runs cosine similarity in PostgreSQL.
    2. Formats retrieved chunks as read-only data blocks to mitigate prompt injection.
    """
    vectorstore = get_vector_store()

    # Query PGVector store directly with automatic embedding and workspace filtering
    results: list[tuple[Document, float]] = vectorstore.similarity_search_with_score(
        query=query,
        k=limit,
        filter={"workspace_id": workspace_id},
    )
    return format_documents_as_readonly_blocks(results)


def delete_document(workspace_id: str, document_id: str) -> dict[str, Any]:
    """
    Completely deletes a document and all related resources from a workspace:
    1. Removes document metadata from PostgreSQL documents table.
    2. Deletes raw file from Neon Object Storage.
    3. Deletes all embedding chunks from PostgreSQL pgvector table.

    Args:
        workspace_id: The UUID boundary of the workspace.
        document_id: The UUID of the document to delete.

    Returns:
        dict[str, Any]: Deletion summary report.
    """
    # 1. Delete from PostgreSQL documents table
    deleted_doc = db_delete_document(workspace_id=workspace_id, document_id=document_id)
    if not deleted_doc:
        raise ValueError(f"Document with ID '{document_id}' not found in workspace.")

    filename = deleted_doc["filename"]
    blob_path = deleted_doc["blob_path"]

    # 2. Delete raw file from Neon Object Storage
    blob_deleted = delete_file_from_blob(blob_path)

    # 3. Delete vector embeddings from pgvector
    chunks_deleted = delete_document_embeddings(workspace_id=workspace_id, document_id=document_id)

    return {
        "success": True,
        "document_id": document_id,
        "filename": filename,
        "blob_path": blob_path,
        "blob_deleted": blob_deleted,
        "chunks_deleted": chunks_deleted,
        "message": f"Successfully deleted '{filename}' and removed {chunks_deleted} vector embeddings.",
    }


def delete_workspace_pipeline(user_id: str, workspace_id: str) -> dict[str, Any]:
    """
    Orchestrates the complete deletion of a workspace and all of its assets:
    1. Removes all vector embeddings in PostgreSQL pgvector.
    2. Deletes all raw blobs in Neon Object Storage under workspaces/{workspace_id}/.
    3. Deletes workspace record from PostgreSQL workspaces table (cascades to documents, tasks, logs).

    Args:
        user_id: The ID of the owning user.
        workspace_id: The UUID of the workspace to delete.

    Returns:
        dict[str, Any]: Deletion summary report.
    """
    # 1. Delete vector embeddings
    vectors_deleted = delete_workspace_embeddings(workspace_id=workspace_id)

    # 2. Delete all S3 blobs
    blobs_deleted = delete_workspace_blobs(workspace_id=workspace_id)

    # 3. Delete workspace DB record (automatically cascades to documents, tasks, logs)
    deleted_ws = db_delete_workspace(user_id=user_id, workspace_id=workspace_id)
    if not deleted_ws:
        raise ValueError(f"Workspace '{workspace_id}' not found or not owned by user.")

    return {
        "success": True,
        "workspace_id": workspace_id,
        "workspace_name": deleted_ws["name"],
        "vectors_deleted": vectors_deleted,
        "blobs_deleted": blobs_deleted,
        "message": f"Successfully deleted workspace '{deleted_ws['name']}'.",
    }
