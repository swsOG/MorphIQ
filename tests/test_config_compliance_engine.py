import importlib
import os
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


def _make_db(tmp_path: Path) -> Path:
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
            key TEXT NOT NULL,
            label TEXT NOT NULL
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
        CREATE TABLE extraction_fields (
            id INTEGER PRIMARY KEY,
            document_type_id INTEGER NOT NULL,
            field_key TEXT NOT NULL,
            field_label TEXT NOT NULL,
            field_order INTEGER NOT NULL DEFAULT 0,
            is_required INTEGER NOT NULL DEFAULT 0,
            include_in_extraction INTEGER NOT NULL DEFAULT 1,
            is_active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE compliance_rules (
            id INTEGER PRIMARY KEY,
            document_type_id INTEGER NOT NULL,
            rule_name TEXT NOT NULL,
            display_label TEXT NOT NULL,
            mandatory INTEGER NOT NULL DEFAULT 1,
            track_expiry INTEGER NOT NULL DEFAULT 1,
            expiry_field_key TEXT,
            expiry_warning_days INTEGER NOT NULL DEFAULT 30,
            rule_order INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE dashboard_config (
            id INTEGER PRIMARY KEY,
            document_type_id INTEGER NOT NULL,
            show_in_dashboard INTEGER NOT NULL DEFAULT 1,
            show_in_upload INTEGER NOT NULL DEFAULT 1,
            show_in_detection INTEGER NOT NULL DEFAULT 1,
            display_order INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1
        );
        """
    )
    conn.executemany(
        "INSERT INTO clients (id, name, deleted_at) VALUES (?, ?, NULL)",
        [(1, "Agency A")],
    )
    conn.executemany(
        "INSERT INTO properties (id, client_id, address, deleted_at) VALUES (?, ?, ?, NULL)",
        [
            (11, 1, "1 Alpha Street"),
            (12, 1, "2 Beta Street"),
            (13, 1, "3 Gamma Street"),
        ],
    )
    conn.executemany(
        "INSERT INTO document_types (id, key, label) VALUES (?, ?, ?)",
        [
            (1, "gas-safety-certificate", "Gas Safety Certificate"),
            (2, "fire-door-certificate", "Fire Door Certificate"),
            (3, "brochure", "Brochure"),
        ],
    )
    conn.executemany(
        """
        INSERT INTO compliance_rules
            (document_type_id, rule_name, display_label, mandatory, track_expiry, expiry_field_key, expiry_warning_days, rule_order, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "gas_safety", "Gas Safety", 1, 1, "expiry_date", 30, 1, 1),
            (2, "fire_door", "Fire Door", 0, 1, "inspection_due", 15, 2, 1),
                (3, "brochure", "Brochure", 1, 0, None, 30, 3, 1),
        ],
    )
    conn.executemany(
        """
        INSERT INTO dashboard_config
            (document_type_id, show_in_dashboard, show_in_upload, show_in_detection, display_order, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (1, 1, 1, 1, 1, 1),
            (2, 1, 1, 1, 2, 1),
            (3, 1, 1, 1, 3, 1),
        ],
    )
    conn.executemany(
        """
        INSERT INTO documents (id, property_id, document_type_id, batch_date, scanned_at, reviewed_at, imported_at, deleted_at)
        VALUES (?, ?, ?, '2026-04-20', '2026-04-20', '2026-04-20', '2026-04-20', NULL)
        """,
        [
            (101, 11, 1),
            (102, 13, 3),
        ],
    )
    conn.executemany(
        "INSERT INTO document_fields (document_id, field_key, field_value, deleted_at) VALUES (?, ?, ?, NULL)",
        [
            (101, "expiry_date", "2030-01-01"),
            (102, "title", "Welcome Pack"),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


class ConfigComplianceEngineTests(unittest.TestCase):
    def test_compliance_engine_uses_database_rules_for_mandatory_expiry_and_no_expiry_types(self):
        with TemporaryDirectory() as tmp_dir:
            db_path = _make_db(Path(tmp_dir))
            with mock.patch.dict(os.environ, {"DATABASE_URL": str(db_path)}, clear=False):
                from portal_new import compliance_engine

                importlib.reload(compliance_engine)
                rows = compliance_engine.evaluate_compliance_for_client(1)

            by_property = {row["property"]: row for row in rows}
            self.assertEqual(by_property["1 Alpha Street"]["gas_safety"], "valid")
            self.assertEqual(by_property["2 Beta Street"]["gas_safety"], "missing")
            self.assertEqual(by_property["2 Beta Street"]["fire_door"], "valid")
            self.assertEqual(by_property["3 Gamma Street"]["brochure"], "valid")


if __name__ == "__main__":
    unittest.main()
