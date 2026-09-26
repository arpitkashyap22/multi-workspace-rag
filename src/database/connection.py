"""
Database connection management module.
Provides high-performance persistent connection pooling using psycopg_pool
and registers the pgvector extension with psycopg3.
"""

from contextlib import contextmanager
from typing import Generator
import psycopg
from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector
import streamlit as st
from src.core.config import get_database_url


@st.cache_resource(show_spinner=False)
def _get_connection_pool() -> ConnectionPool:
    """
    Creates a singleton psycopg connection pool cached across the Streamlit application lifecycle.
    Maintains warm, authenticated SSL connections to PostgreSQL, eliminating SSL handshake latency.
    """
    db_url = get_database_url()
    pool = ConnectionPool(
        conninfo=db_url,
        min_size=2,
        max_size=10,
        timeout=15.0,
        configure=register_vector,
        open=True,
    )
    return pool


@contextmanager
def get_db_connection() -> Generator[psycopg.Connection, None, None]:
    """
    Yields a pooled, pre-authenticated PostgreSQL connection with pgvector registered.
    Reuses existing connections in memory for sub-millisecond execution.
    Automatically returns the connection to the pool when the context manager exits.
    """
    try:
        pool = _get_connection_pool()
        with pool.connection() as conn:
            yield conn
    except Exception:
        # Fallback to direct connection if pooling experiences any transient issue
        db_url = get_database_url()
        with psycopg.connect(db_url) as direct_conn:
            register_vector(direct_conn)
            yield direct_conn
