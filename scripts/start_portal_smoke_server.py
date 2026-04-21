import os
import sqlite3
import sys
import tempfile
from pathlib import Path

from werkzeug.security import generate_password_hash


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PORTAL_DIR = PROJECT_ROOT / "portal_new"
TEMP_ROOT = Path(tempfile.mkdtemp(prefix="morphiq-smoke-"))
CLIENTS_DIR = TEMP_ROOT / "Clients"
DB_PATH = TEMP_ROOT / "portal.db"


def seed_portal_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE clients (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                slug TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                deleted_at TEXT
            );
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                client_id INTEGER,
                password_hash TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                deleted_at TEXT,
                last_login TEXT
            );
            CREATE TABLE properties (
                id INTEGER PRIMARY KEY,
                client_id INTEGER NOT NULL,
                address TEXT NOT NULL,
                deleted_at TEXT
            );
            CREATE TABLE document_types (
                id INTEGER PRIMARY KEY,
                key TEXT NOT NULL,
                label TEXT NOT NULL
            );
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                property_id INTEGER NOT NULL,
                client_id INTEGER NOT NULL,
                document_type_id INTEGER,
                source_doc_id TEXT,
                doc_name TEXT NOT NULL,
                status TEXT,
                pdf_path TEXT,
                quality_score REAL,
                reviewed_by TEXT,
                reviewed_at TEXT,
                scanned_at TEXT,
                batch_date TEXT,
                imported_at TEXT,
                deleted_at TEXT
            );
            CREATE TABLE document_fields (
                id INTEGER PRIMARY KEY,
                document_id INTEGER NOT NULL,
                field_key TEXT NOT NULL,
                field_label TEXT,
                field_value TEXT,
                deleted_at TEXT
            );
            """
        )
        password_hash = generate_password_hash("Password123!")
        conn.executemany(
            "INSERT INTO clients (id, name, slug, is_active, deleted_at) VALUES (?, ?, ?, 1, NULL)",
            [
                (28, "Sample Agency Alpha", "sample-agency-alpha"),
                (30, "Sample Agency Beta", "sample-agency-beta"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO users
                (id, email, full_name, role, client_id, password_hash, is_active, deleted_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, NULL)
            """,
            [
                (1, "admin@example.test", "Platform Admin", "admin", None, password_hash),
                (2, "manager@example.test", "Sample Manager", "manager", 30, password_hash),
            ],
        )
        conn.execute(
            "INSERT INTO properties (id, client_id, address, deleted_at) VALUES (?, ?, ?, NULL)",
            (102, 30, "202 Demo Avenue, Mockford, ZX2 2BB"),
        )
        conn.execute(
            "INSERT INTO document_types (id, key, label) VALUES (?, ?, ?)",
            (2, "tenancy-agreement", "Tenancy Agreement"),
        )
        conn.execute(
            """
            INSERT INTO documents
                (id, property_id, client_id, document_type_id, source_doc_id, doc_name, status,
                 pdf_path, quality_score, reviewed_by, reviewed_at, scanned_at, batch_date, imported_at, deleted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, '', NULL, ?, ?, ?, ?, ?, NULL)
            """,
            (
                1002,
                102,
                30,
                2,
                "BETA-TENANCY-001",
                "Sample Tenancy",
                "verified",
                "Platform Admin",
                "2026-04-02T09:30:00",
                "2026-04-02T09:00:00",
                "2026-04-02",
                "2026-04-02T09:05:00",
            ),
        )
        conn.executemany(
            """
            INSERT INTO document_fields
                (document_id, field_key, field_label, field_value, deleted_at)
            VALUES (?, ?, ?, ?, NULL)
            """,
            [
                (1002, "tenant_full_name", "Tenant Full Name", "Alex Tenant"),
                (1002, "property_address", "Property Address", "202 Demo Avenue, Mockford, ZX2 2BB"),
            ],
        )
        conn.commit()
    finally:
        conn.close()


def seed_clients_dir(clients_dir: Path) -> None:
    doc_dir = clients_dir / "Sample Agency Beta" / "Batches" / "2026-04-02" / "BETA-TENANCY-001"
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / "review.json").write_text(
        '{"status":"Verified","review":{"reviewed_by":"Platform Admin","reviewed_at":"2026-04-02T09:30:00"}}\n',
        encoding="utf-8",
    )


def main() -> None:
    seed_portal_db(DB_PATH)
    seed_clients_dir(CLIENTS_DIR)

    os.environ["DATABASE_URL"] = str(DB_PATH)
    os.environ["MORPHIQ_CLIENTS_DIR"] = str(CLIENTS_DIR)
    os.environ.setdefault("PORTAL_SECRET_KEY", "morphiq-smoke-secret")

    sys.path.insert(0, str(PROJECT_ROOT))
    sys.path.insert(0, str(PORTAL_DIR))

    from portal_new.app import app  # noqa: WPS433

    port = int(os.environ.get("MORPHIQ_SMOKE_PORT", "5015"))
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
