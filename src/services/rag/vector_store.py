"""
LangChain PostgreSQL Vector Store module.
Provides PGVector initialization and configuration powered by psycopg (v3).
"""

from langchain_postgres.vectorstores import PGVector
from src.core.config import get_psycopg_database_url
from src.database.connection import get_db_connection
from src.services.rag.embeddings import get_embeddings_model


def get_vector_store(collection_name: str = "workspace_documents") -> PGVector:
    """
    Returns an initialized LangChain PGVector instance connected to PostgreSQL
    via the modern psycopg driver and SQLAlchemy integration.
    """
    embeddings = get_embeddings_model()
    connection_url = get_psycopg_database_url()

    vector_store = PGVector(
        embeddings=embeddings,
        connection=connection_url,
        collection_name=collection_name,
        use_jsonb=True,
    )
    vector_store.create_tables_if_not_exists()
    return vector_store


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
                (str(document_id), str(workspace_id)),
            )
            deleted_count = cur.rowcount
            conn.commit()
            return deleted_count
