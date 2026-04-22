import importlib
import sqlite3
import unittest


def _make_db(tmp_path):
    db_path = tmp_path / "portal.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE clients (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            deleted_at TEXT
        );
        CREATE TABLE properties (
            id INTEGER PRIMARY KEY,
            client_id INTEGER NOT NULL,
            address TEXT NOT NULL,
            deleted_at TEXT
        );
        CREATE TABLE document_types (
            id INTEGER PRIMARY KEY,
            key TEXT NOT NULL
        );
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY,
            property_id INTEGER NOT NULL,
            document_type_id INTEGER NOT NULL,
            batch_date TEXT,
            scanned_at TEXT,
            reviewed_at TEXT,
            imported_at TEXT,
            deleted_at TEXT
        );
        CREATE TABLE document_fields (
            id INTEGER PRIMARY KEY,
            document_id INTEGER NOT NULL,
            field_key TEXT NOT NULL,
            field_value TEXT,
            deleted_at TEXT
        );
        """
    )
    conn.executemany(
        "INSERT INTO clients (id, name, deleted_at) VALUES (?, ?, NULL)",
        [(1, "Agency A"), (2, "Agency B")],
    )
    conn.executemany(
        "INSERT INTO properties (id, client_id, address, deleted_at) VALUES (?, ?, ?, NULL)",
        [(11, 1, "1 Alpha Street"), (22, 2, "2 Beta Street")],
    )
    conn.executemany(
        "INSERT INTO document_types (id, key) VALUES (?, ?)",
        [(1, "gas-safety-certificate"), (2, "eicr"), (3, "epc"), (4, "deposit-protection")],
    )
    conn.executemany(
        """
        INSERT INTO documents (id, property_id, document_type_id, batch_date, scanned_at, reviewed_at, imported_at, deleted_at)
        VALUES (?, ?, ?, '2026-04-20', '2026-04-20', '2026-04-20', '2026-04-20', NULL)
        """,
        [(101, 11, 1), (202, 22, 1)],
    )
    conn.executemany(
        "INSERT INTO document_fields (document_id, field_key, field_value, deleted_at) VALUES (?, ?, ?, NULL)",
        [(101, "expiry_date", "2030-01-01"), (202, "expiry_date", "2030-01-01")],
    )
    conn.commit()
    conn.close()
    return db_path


class ComplianceEngineTests(unittest.TestCase):
    def test_evaluate_compliance_for_client_returns_only_requested_client(self):
        from tempfile import TemporaryDirectory
        import os
        from unittest import mock

        with TemporaryDirectory() as tmp_dir:
            from pathlib import Path

            db_path = _make_db(Path(tmp_dir))
            with mock.patch.dict(os.environ, {"DATABASE_URL": str(db_path)}, clear=False):
                from portal_new import compliance_engine

                importlib.reload(compliance_engine)

                rows = compliance_engine.evaluate_compliance_for_client(1)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["client"], "Agency A")
            self.assertEqual(rows[0]["property"], "1 Alpha Street")


if __name__ == "__main__":
    unittest.main()
