import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(r"C:\Users\user\Projects\MorphIQ\Product")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AutoOcrWatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.auto_ocr_watch = load_module(
            "auto_ocr_watch_live",
            PROJECT_ROOT / "auto_ocr_watch.py",
        )

    def test_write_review_json_preserves_initial_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_folder = Path(tmpdir)

            review_path = self.auto_ocr_watch.write_review_json(
                doc_folder=doc_folder,
                doc_id="DOC-00001",
                pdf_name="doc.pdf",
                image_name="doc.jpg",
                template={},
                doc_name="Tenancy Agreement",
                initial_fields={"property_address": "101 Example Street"},
            )

            with review_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)

        self.assertEqual(
            payload["fields"],
            {"property_address": "101 Example Street"},
        )
        self.assertEqual(payload["doc_name"], "Tenancy Agreement")


class AiPrefillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ai_prefill = load_module(
            "ai_prefill_live",
            PROJECT_ROOT / "ai_prefill.py",
        )

    def test_get_ai_provider_defaults_to_gemini(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.ai_prefill.get_ai_provider(), "gemini")

    def test_call_model_with_pdf_routes_to_gemini_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(
                self.ai_prefill,
                "call_gemini_with_pdf",
                return_value="gemini-result",
            ) as gemini_mock:
                with mock.patch.object(
                    self.ai_prefill,
                    "call_claude_with_pdf",
                    return_value="anthropic-result",
                ) as anthropic_mock:
                    result = self.ai_prefill.call_model_with_pdf(
                        pdf_b64="abc123",
                        system_prompt="system",
                        user_prompt="user",
                    )

        self.assertEqual(result, "gemini-result")
        gemini_mock.assert_called_once_with(
            "abc123",
            "system",
            "user",
            model="gemini-2.5-flash",
        )
        anthropic_mock.assert_not_called()


class SyncToPortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sync_to_portal = load_module(
            "sync_to_portal_live",
            PROJECT_ROOT / "sync_to_portal.py",
        )

    def make_conn(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(
            """
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                property_id INTEGER,
                document_type_id INTEGER,
                source_doc_id TEXT,
                doc_name TEXT,
                deleted_at TEXT
            );
            CREATE TABLE document_fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                field_key TEXT,
                field_label TEXT,
                field_value TEXT,
                source TEXT,
                updated_at TEXT
            );
            CREATE TABLE pack_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pack_id INTEGER NOT NULL,
                document_id INTEGER NOT NULL
            );
            CREATE TABLE properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                address TEXT NOT NULL,
                postcode TEXT
            );
            """
        )
        return conn

    def test_ensure_property_reuses_unassigned_placeholder(self):
        conn = self.make_conn()
        try:
            first_id = self.sync_to_portal.ensure_property(conn, 9, "")
            second_id = self.sync_to_portal.ensure_property(conn, 9, "   ")
            row = conn.execute(
                "SELECT address FROM properties WHERE id = ?",
                (first_id,),
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(first_id, second_id)
        self.assertEqual(row["address"], "Unassigned property")

    def test_find_existing_document_reuses_seeded_row_for_doc_import(self):
        conn = self.make_conn()
        try:
            cur = conn.execute(
                """
                INSERT INTO documents
                    (client_id, property_id, document_type_id, source_doc_id, doc_name, deleted_at)
                VALUES (?, ?, ?, ?, ?, NULL)
                """,
                (3, 44, 7, "seeded-tenancy-1", "Tenancy Agreement"),
            )
            seeded_id = cur.lastrowid

            existing = self.sync_to_portal.find_existing_document(
                conn,
                client_id=3,
                source_doc_id="DOC-00001",
                property_id=44,
                doc_type_id=7,
                doc_name="Tenancy Agreement",
                batch_date="2026-04-20",
            )
        finally:
            conn.close()

        self.assertIsNotNone(existing)
        self.assertEqual(existing["id"], seeded_id)
        self.assertEqual(existing["property_id"], 44)

    def test_find_existing_document_merges_legacy_duplicate_rows(self):
        conn = self.make_conn()
        try:
            legacy_id = conn.execute(
                """
                INSERT INTO documents
                    (client_id, property_id, document_type_id, source_doc_id, doc_name, deleted_at)
                VALUES (?, ?, ?, ?, ?, NULL)
                """,
                (4, 88, 5, "DOC-00002", "Gas Safety Certificate"),
            ).lastrowid
            canonical_id = conn.execute(
                """
                INSERT INTO documents
                    (client_id, property_id, document_type_id, source_doc_id, doc_name, deleted_at)
                VALUES (?, ?, ?, ?, ?, NULL)
                """,
                (4, 88, 5, "2026-04-20__DOC-00002", "Gas Safety Certificate"),
            ).lastrowid
            conn.execute(
                """
                INSERT INTO document_fields
                    (document_id, field_key, field_label, field_value, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                (legacy_id, "certificate_number", "Certificate Number", "GS-123", "review_json"),
            )

            existing = self.sync_to_portal.find_existing_document(
                conn,
                client_id=4,
                source_doc_id="DOC-00002",
                property_id=88,
                doc_type_id=5,
                doc_name="Gas Safety Certificate",
                batch_date="2026-04-20",
            )

            remaining_docs = conn.execute(
                "SELECT id, source_doc_id FROM documents ORDER BY id"
            ).fetchall()
            merged_field = conn.execute(
                """
                SELECT field_value
                FROM document_fields
                WHERE document_id = ? AND field_key = 'certificate_number'
                """,
                (canonical_id,),
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(existing)
        self.assertEqual(existing["id"], canonical_id)
        self.assertEqual(len(remaining_docs), 1)
        self.assertEqual(remaining_docs[0]["source_doc_id"], "2026-04-20__DOC-00002")
        self.assertEqual(merged_field["field_value"], "GS-123")


if __name__ == "__main__":
    unittest.main()
