"""
Database connection management.
Provides connection pooling / instantiation and registers the pgvector extension with psycopg3.
"""

import psycopg
from pgvector.psycopg import register_vector
from src.core.config import get_database_url


def get_db_connection() -> psycopg.Connection:
    """
    Connect to PostgreSQL using psycopg and register the pgvector extension.
    """
    db_url = get_database_url()
    conn = psycopg.connect(db_url)
    register_vector(conn)
    return conn
