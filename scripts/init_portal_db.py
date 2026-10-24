"""Create the core portal tables in portal.db (safe to run on an existing database).

Usage:
    python scripts/init_portal_db.py                 # portal.db in the project root
    python scripts/init_portal_db.py path/to/portal.db
    DATABASE_URL=path/to/portal.db python scripts/init_portal_db.py
"""
import os
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "portal_new" / "schema.sql"


def default_db_path() -> Path:
    return Path(os.environ.get("DATABASE_URL") or PROJECT_ROOT / "portal.db")


def init_db(db_path: Path) -> Path:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()
    return db_path


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else default_db_path()
    path = init_db(target)
    print(f"Core portal schema ready: {path}")


if __name__ == "__main__":
    main()
