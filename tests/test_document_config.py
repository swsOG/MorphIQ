import importlib
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\user\Projects\MorphIQ\Product")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _make_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "portal.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE document_types (
                id INTEGER PRIMARY KEY,
                key TEXT NOT NULL,
                label TEXT NOT NULL
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
            "INSERT INTO document_types (id, key, label) VALUES (?, ?, ?)",
            [
                (1, "gas-safety-certificate", "Gas Safety Certificate"),
                (2, "fire-door-certificate", "Fire Door Certificate"),
                (3, "legacy-deposit-protection", "Legacy Deposit Protection"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO extraction_fields
                (document_type_id, field_key, field_label, field_order, is_required, include_in_extraction, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "property_address", "Property Address", 1, 1, 1, 1),
                (1, "engineer_name", "Engineer Name", 2, 1, 1, 1),
                (1, "expiry_date", "Expiry Date", 3, 1, 1, 1),
                (2, "property_address", "Property Address", 1, 1, 1, 1),
                (2, "door_location", "Door Location", 2, 1, 1, 1),
                (2, "inspection_date", "Inspection Date", 3, 1, 1, 1),
                (3, "property_address", "Property Address", 1, 1, 1, 1),
            ],
        )
        conn.executemany(
            """
            INSERT INTO compliance_rules
                (document_type_id, rule_name, display_label, mandatory, track_expiry, expiry_field_key, expiry_warning_days, rule_order, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "gas_safety", "Gas Safety Certificate", 1, 1, "expiry_date", 30, 1, 1),
                    (2, "fire_door", "Fire Door Certificate", 0, 0, None, 30, 2, 1),
                (3, "legacy_deposit", "Legacy Deposit Protection", 1, 1, "expiry_date", 30, 3, 0),
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
                (3, 0, 0, 0, 3, 0),
            ],
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


class DocumentConfigTests(unittest.TestCase):
    def test_live_default_config_seeds_fire_door_certificate(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "portal.db"
            conn = sqlite3.connect(db_path)
            try:
                conn.execute(
                    """
                    CREATE TABLE document_types (
                        id INTEGER PRIMARY KEY,
                        key TEXT NOT NULL
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()

            with unittest.mock.patch.dict(os.environ, {"DATABASE_URL": str(db_path)}, clear=False):
                from portal_new import document_config

                importlib.reload(document_config)
                document_config.ensure_document_config(str(db_path))
                config = document_config.find_document_config("Fire Door Certificate", str(db_path))

            self.assertIsNotNone(config)
            self.assertEqual(config["document_key"], "fire-door-certificate")
            self.assertEqual(
                config["field_keys"],
                [
                    "property_address",
                    "certificate_number",
                    "door_location",
                    "inspection_date",
                    "result",
                    "next_inspection_date",
                ],
            )
            self.assertEqual(
                config["required_fields"],
                [
                    "property_address",
                    "certificate_number",
                    "door_location",
                    "inspection_date",
                    "result",
                ],
            )

    def test_ai_prefill_reads_new_document_type_from_database_config(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = _make_db(Path(tmp_dir))
            with unittest.mock.patch.dict(os.environ, {"DATABASE_URL": str(db_path)}, clear=False):
                import ai_prefill

                importlib.reload(ai_prefill)
                config = ai_prefill.get_document_config("Fire Door Certificate")

            self.assertIsNotNone(config)
            self.assertEqual(config["document_key"], "fire-door-certificate")
            self.assertEqual(
                config["field_keys"],
                [
                    "property_address",
                    "certificate_number",
                    "door_location",
                    "inspection_date",
                    "result",
                    "next_inspection_date",
                ],
            )
            self.assertEqual(
                config["required_fields"],
                [
                    "property_address",
                    "certificate_number",
                    "door_location",
                    "inspection_date",
                    "result",
                ],
            )

    def test_inactive_document_types_are_ignored_by_runtime_config_readers(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = _make_db(Path(tmp_dir))
            with unittest.mock.patch.dict(os.environ, {"DATABASE_URL": str(db_path)}, clear=False):
                import ai_prefill
                from portal_new import document_config

                importlib.reload(ai_prefill)
                importlib.reload(document_config)
                labels = document_config.get_detection_document_labels(str(db_path))
                config = ai_prefill.get_document_config("Legacy Deposit Protection")

            self.assertNotIn("Legacy Deposit Protection", labels)
            self.assertIsNone(config)


if __name__ == "__main__":
    unittest.main()
