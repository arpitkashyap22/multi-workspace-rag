"""
LangChain PostgreSQL Vector Store module.
Provides PGVector initialization and configuration powered by psycopg (v3).
"""

import streamlit as st
from langchain_postgres.vectorstores import PGVector
from src.core.config import get_psycopg_database_url
from src.database.connection import get_db_connection
from src.services.rag.embeddings import get_embeddings_model


@st.cache_resource(show_spinner=False)
def ensure_vector_tables_exist(collection_name: str = "workspace_documents") -> None:
    """Ensures vector store tables and schemas are initialized once per application lifetime."""
    embeddings = get_embeddings_model()
    connection_url = get_psycopg_database_url()
    vs = PGVector(
        embeddings=embeddings,
        connection=connection_url,
        collection_name=collection_name,
        use_jsonb=True,
    )
    vs.create_tables_if_not_exists()


@st.cache_resource(show_spinner=False)
def get_vector_store(collection_name: str = "workspace_documents") -> PGVector:
    """
    Returns an initialized, cached LangChain PGVector instance connected to PostgreSQL
    via the modern psycopg driver and SQLAlchemy integration without redundant table DDL checks.
    """
    embeddings = get_embeddings_model()
    connection_url = get_psycopg_database_url()

    return PGVector(
        embeddings=embeddings,
        connection=connection_url,
        collection_name=collection_name,
        use_jsonb=True,
    )


def delete_document_embeddings(workspace_id: str, document_id: str) -> int:
    """
    Deletes all vector embeddings belonging to a specific document and workspace
    from the langchain_pg_embedding table.

    Args:
        workspace_id: The UUID boundary of the workspace.
        document_id: The UUID of the document.

    Returns:
        int: Number of deleted embedding chunk rows.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM langchain_pg_embedding
                WHERE cmetadata->>'document_id' = %s
                  AND cmetadata->>'workspace_id' = %s;
                """,
                (document_id, workspace_id),
            )
            deleted_count = cur.rowcount
            conn.commit()
            return deleted_count


def delete_workspace_embeddings(workspace_id: str) -> int:
    """
    Deletes all vector embeddings belonging to a workspace from langchain_pg_embedding.

    Args:
        workspace_id: The UUID boundary of the workspace.

    Returns:
        int: Number of deleted embedding rows.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM langchain_pg_embedding
                WHERE cmetadata->>'workspace_id' = %s;
                """,
                (workspace_id,),
            )
            deleted_count = cur.rowcount
            conn.commit()
            return deleted_count
