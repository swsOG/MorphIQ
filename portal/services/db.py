"""Database helpers for portal service layer."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager


def get_database_url() -> str:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return dsn


@contextmanager
def get_cursor(dict_rows: bool = True):
    """
    Yield a DB cursor based on DATABASE_URL.

    - sqlite:///path/to.db  -> sqlite3 connection
    - postgresql://...      -> psycopg2 connection
    - postgres://...        -> psycopg2 connection
    """
    dsn = get_database_url()

    # SQLite mode (development)
    if dsn.startswith("sqlite:///"):
        db_path = dsn[len("sqlite:///") :]
        conn = sqlite3.connect(db_path)
        try:
            if dict_rows:
                conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            try:
                yield cur
                conn.commit()
            finally:
                cur.close()
        finally:
            conn.close()
        return

    # PostgreSQL mode (production)
    if dsn.startswith("postgresql://") or dsn.startswith("postgres://"):
        import psycopg2
        from psycopg2.extras import DictCursor

        with psycopg2.connect(dsn) as conn:
            cursor_factory = DictCursor if dict_rows else None
            with conn.cursor(cursor_factory=cursor_factory) as cur:
                yield cur
        return

    raise RuntimeError("Unsupported database type")
