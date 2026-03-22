import os
import sqlite3
from datetime import datetime


def get_db_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.environ.get("DATABASE_URL", os.path.join(base_dir, "..", "portal.db"))


def users_table_exists(conn: sqlite3.Connection) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
    )
    row = cur.fetchone()
    return bool(row)


def create_users_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'manager',
            client_id INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            last_login TEXT
        )
        """
    )
    conn.commit()


def main() -> None:
    db_path = get_db_path()
    print(f"Using portal database at: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        if users_table_exists(conn):
            print("users table already exists — nothing to do.")
            return

        create_users_table(conn)
        now = datetime.utcnow().isoformat(timespec="seconds")
        print(f"users table created successfully at {now}.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

