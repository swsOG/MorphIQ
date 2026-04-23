import importlib.util
import io
import json
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


def seed_config_db(db_path: Path):
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE document_types (
                id INTEGER PRIMARY KEY,
                key TEXT NOT NULL,
                label TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                has_expiry INTEGER NOT NULL DEFAULT 0,
                expiry_field_key TEXT
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
        conn.execute(
            """
            INSERT INTO document_types (id, key, label, is_active, has_expiry, expiry_field_key)
            VALUES (1, 'fire-door-certificate', 'Fire Door Certificate', 1, 0, NULL)
            """
        )
        conn.executemany(
            """
            INSERT INTO extraction_fields
                (document_type_id, field_key, field_label, field_order, is_required, include_in_extraction, is_active)
            VALUES (?, ?, ?, ?, ?, 1, 1)
            """,
            [
                (1, "property_address", "Property Address", 1, 1),
                (1, "door_location", "Door Location", 2, 1),
                (1, "inspection_date", "Inspection Date", 3, 1),
            ],
        )
        conn.execute(
            """
            INSERT INTO compliance_rules
                (document_type_id, rule_name, display_label, mandatory, track_expiry, expiry_field_key, expiry_warning_days, rule_order, is_active)
            VALUES (1, 'fire_door', 'Fire Door Certificate', 0, 0, NULL, 30, 1, 1)
            """
        )
        conn.execute(
            """
            INSERT INTO dashboard_config
                (document_type_id, show_in_dashboard, show_in_upload, show_in_detection, display_order, is_active)
            VALUES (1, 1, 1, 1, 1, 1)
            """
        )
        conn.commit()
    finally:
        conn.close()


class ScanStationWiringTests(unittest.TestCase):
    def test_scanstation_html_matches_simplified_camera_first_contract(self):
        html = (PROJECT_ROOT / "scan_station.html").read_text(encoding="utf-8")

        self.assertIn("Import Document", html)
        self.assertIn("Review Before Save", html)
        self.assertIn("Intake Summary", html)
        self.assertIn("Current client", html)
        self.assertNotIn("Select Folder", html)
        self.assertNotIn("Export Verified", html)
        self.assertNotIn("Quality Dashboard", html)
        self.assertNotIn("Session progress", html)
        self.assertNotIn("Live Session Summary", html)
        self.assertNotIn("Quick</button>", html)
        self.assertNotIn("Careful</button>", html)

    def test_scanstation_guide_matches_camera_first_fallback_import_model(self):
        guide = (PROJECT_ROOT / "docs" / "User_Guide" / "01_ScanStation.md").read_text(encoding="utf-8")

        self.assertIn("camera-first", guide.lower())
        self.assertIn("Import Document", guide)
        self.assertIn("Review Before Save", guide)
        self.assertNotIn("Select Folder", guide)
        self.assertNotIn("Export Verified", guide)

    def test_backend_intake_saves_uploaded_pdf_into_canonical_raw_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "Clients").mkdir(parents=True)
            db_path = base / "portal.db"
            seed_config_db(db_path)

            with mock.patch.dict(
                "os.environ",
                {"MORPHIQ_BASE": str(base), "DATABASE_URL": str(db_path)},
                clear=False,
            ):
                server = load_module(
                    f"server_intake_test_{base.name}",
                    PROJECT_ROOT / "server.py",
                )
                client = server.app.test_client()
                response = client.post(
                    "/intake/Epping Lettings",
                    data={
                        "file": (io.BytesIO(b"%PDF-1.4 fire door test"), "fire_door_certificate_sample.pdf"),
                        "doc_name": "Fire Door Certificate Sample",
                        "property_address": "12 Oak Street",
                    },
                    content_type="multipart/form-data",
                )

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            raw_name = payload["raw_name"]
            raw_path = base / "Clients" / "Epping Lettings" / "raw" / raw_name
            meta_path = base / "Clients" / "Epping Lettings" / "raw" / f"{raw_name}.meta.json"

            self.assertTrue(raw_path.exists())
            self.assertEqual(raw_path.suffix.lower(), ".pdf")
            self.assertTrue(meta_path.exists())
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self.assertEqual(meta["doc_name"], "Fire Door Certificate Sample")
            self.assertEqual(meta["property_address"], "12 Oak Street")

    def test_docs_endpoint_exposes_config_backed_review_metadata_for_new_types(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            doc_folder = base / "Clients" / "Epping Lettings" / "Batches" / "2026-04-23" / "DOC-00001"
            doc_folder.mkdir(parents=True, exist_ok=True)
            (doc_folder / "fire-door.pdf").write_bytes(b"%PDF-1.4 test")
            (doc_folder / "review.json").write_text(
                json.dumps(
                    {
                        "doc_id": "DOC-00001",
                        "doc_type": "Fire Door Certificate",
                        "status": "New",
                        "files": {"pdf": "fire-door.pdf", "raw_image": "", "raw_source": "fire-door.pdf"},
                        "fields": {"property_address": "12 Oak Street"},
                        "review": {"scanned_at": "2026-04-23 10:00:00"},
                    }
                ),
                encoding="utf-8",
            )
            db_path = base / "portal.db"
            seed_config_db(db_path)

            with mock.patch.dict(
                "os.environ",
                {"MORPHIQ_BASE": str(base), "DATABASE_URL": str(db_path)},
                clear=False,
            ):
                server = load_module(
                    f"server_docs_test_{base.name}",
                    PROJECT_ROOT / "server.py",
                )
                client = server.app.test_client()
                response = client.get("/docs/Epping Lettings")

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(len(payload["docs"]), 1)
            doc = payload["docs"][0]
            self.assertEqual(doc["doc_type"], "Fire Door Certificate")
            self.assertEqual(
                doc["required_fields"],
                ["property_address", "door_location", "inspection_date"],
            )
            self.assertEqual(
                [field["field_key"] for field in doc["field_definitions"]],
                ["property_address", "door_location", "inspection_date"],
            )

    def test_pdf_raw_files_are_processed_without_image_preprocessing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            raw_folder = tmp_path / "raw"
            batches_folder = tmp_path / "Batches"
            raw_folder.mkdir(parents=True)
            batches_folder.mkdir(parents=True)
            pdf_path = raw_folder / "fire_door_certificate_sample.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 fire door input")
            meta_path = raw_folder / "fire_door_certificate_sample.pdf.meta.json"
            meta_path.write_text(
                json.dumps(
                    {
                        "doc_name": "Fire Door Certificate Sample",
                        "property_address": "12 Oak Street",
                    }
                ),
                encoding="utf-8",
            )

            auto_ocr_watch = load_module(
                f"auto_ocr_pdf_test_{tmp_path.name}",
                PROJECT_ROOT / "auto_ocr_watch.py",
            )

            def fake_ocr_to_pdf(input_path: Path, output_path: Path, client_name: str):
                output_path.write_bytes(b"%PDF-1.4 normalized")

            with mock.patch.object(auto_ocr_watch, "TEMP", tmp_path / "temp"), \
                 mock.patch.object(auto_ocr_watch, "preprocess_for_ocr", side_effect=AssertionError("PDF imports should skip image preprocessing")), \
                 mock.patch.object(auto_ocr_watch, "ocr_to_pdf", side_effect=fake_ocr_to_pdf), \
                 mock.patch.object(auto_ocr_watch, "run_ai_prefill"), \
                 mock.patch.object(auto_ocr_watch, "sync_single_doc"):
                auto_ocr_watch.process_file(pdf_path, raw_folder, batches_folder, "Epping Lettings")

            doc_folder = next((batches_folder / next(iter([p.name for p in batches_folder.iterdir()]))).iterdir())
            review = json.loads((doc_folder / "review.json").read_text(encoding="utf-8"))

            self.assertTrue((doc_folder / "fire_door_certificate_sample.pdf").exists())
            self.assertEqual(review["files"]["pdf"], "fire_door_certificate_sample.pdf")
            self.assertEqual(review["files"]["raw_image"], "")
            self.assertEqual(review["files"]["raw_source"], "fire_door_certificate_sample.pdf")
            self.assertEqual(review["fields"]["property_address"], "12 Oak Street")


if __name__ == "__main__":
    unittest.main()
