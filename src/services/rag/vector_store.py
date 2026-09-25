"""
LangChain PostgreSQL Vector Store module.
Provides PGVector initialization and configuration powered by psycopg (v3).
"""

from langchain_postgres.vectorstores import PGVector
from src.core.config import get_psycopg_database_url
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
