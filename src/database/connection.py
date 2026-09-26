"""
Database connection management module.
Provides resilient connection pooling using psycopg_pool configured for Neon serverless PostgreSQL,
with automatic stale connection eviction, health check validation, and pgvector registration.
"""

from contextlib import contextmanager, suppress
from typing import Generator
import psycopg
from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector
import streamlit as st
from src.core.config import get_database_url


@st.cache_resource(show_spinner=False)
def _get_connection_pool() -> ConnectionPool:
    """
    Creates a singleton psycopg connection pool optimized for Neon serverless PostgreSQL:
    - min_size=0: Does not hoard idle connections when database compute auto-suspends.
    - check=ConnectionPool.check_connection: Validates connection health before checkout,
      automatically evicting stale/closed connections from serverless scale-down.
    - max_idle=60: Recycles idle connections after 60 seconds.
    - max_lifetime=300: Refreshes connections within Neon's 5-minute idle compute window.
    - timeout=30.0: Allows Neon compute to wake up smoothly without timeouts.
    """
    db_url = get_database_url()
    pool = ConnectionPool(
        conninfo=db_url,
        min_size=0,
        max_size=10,
        timeout=30.0,
        max_idle=60.0,
        max_lifetime=300.0,
        check=ConnectionPool.check_connection,
        configure=register_vector,
        open=True,
    )
    return pool


@contextmanager
def get_db_connection() -> Generator[psycopg.Connection, None, None]:
    """
    Yields a validated, healthy PostgreSQL connection with pgvector registered.
    Complies strictly with the Python generator context manager protocol (single yield)
    to eliminate 'RuntimeError: generator didn't stop after throw()'.
    """
    conn = None
    ctx = None
    use_pool = False

    try:
        pool = _get_connection_pool()
        ctx = pool.connection()
        conn = ctx.__enter__()
        use_pool = True
    except Exception:
        # Fallback to direct connection if pool checkout fails
        try:
            db_url = get_database_url()
            conn = psycopg.connect(db_url)
            register_vector(conn)
            use_pool = False
        except Exception:
            raise

    try:
        yield conn
    finally:
        if use_pool and ctx:
            with suppress(Exception):
                ctx.__exit__(None, None, None)
        elif conn:
            with suppress(Exception):
                conn.close()
