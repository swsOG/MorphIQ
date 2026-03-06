"""Filesystem importer for existing ScanSystem DOC folders.

This importer reads local client batch folders, parses review.json + PDF references,
and upserts data into the portal PostgreSQL schema.

Design constraints:
- Never moves source files.
- Stores file paths by reference only.
- Supports incremental re-runs using upserts keyed by (client_id, source_doc_id).
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any



SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
TENANCY_DOC_TYPES = {"tenancy agreement", "tenancy agreements"}


@dataclass
class ImportStats:
    scanned_docs: int = 0
    imported_docs: int = 0
    updated_docs: int = 0
    skipped_docs: int = 0
    field_rows: int = 0
    properties_linked: int = 0
    tenants_linked: int = 0


class FilesystemImporter:
    """Incremental importer from DOC folders into portal DB."""

    def __init__(self, dsn: str, client_name: str, client_root: Path) -> None:
        self.dsn = dsn
        self.client_name = client_name.strip()
        self.client_root = client_root
        self.batches_root = client_root / "Batches"
        self.stats = ImportStats()

    def run(self) -> ImportStats:
        if not self.batches_root.exists():
            raise FileNotFoundError(f"Batches folder not found: {self.batches_root}")

        import psycopg2
        from psycopg2.extras import DictCursor

        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                client_id = self._get_or_create_client(cur)
                for review_path in self._iter_review_files():
                    self.stats.scanned_docs += 1
                    try:
                        self._import_doc(cur, client_id, review_path)
                    except Exception:
                        self.stats.skipped_docs += 1
                        raise

        return self.stats

    def _iter_review_files(self):
        for date_folder in sorted(self.batches_root.iterdir()):
            if not date_folder.is_dir():
                continue
            for doc_folder in sorted(date_folder.iterdir()):
                if not doc_folder.is_dir() or not doc_folder.name.startswith("DOC-"):
                    continue
                review_path = doc_folder / "review.json"
                if review_path.exists():
                    yield review_path

    def _get_or_create_client(self, cur) -> int:
        slug = _slugify(self.client_name)
        cur.execute("SELECT id FROM clients WHERE slug = %s", (slug,))
        row = cur.fetchone()
        if row:
            return int(row["id"])

        cur.execute(
            """
            INSERT INTO clients (name, slug, is_active)
            VALUES (%s, %s, TRUE)
            RETURNING id
            """,
            (self.client_name, slug),
        )
        return int(cur.fetchone()["id"])

    def _import_doc(self, cur, client_id: int, review_path: Path) -> None:
        payload = _read_json(review_path)
        doc_folder = review_path.parent
        date_folder = doc_folder.parent

        source_doc_id = str(payload.get("doc_id") or doc_folder.name)
        if not source_doc_id.startswith("DOC-"):
            self.stats.skipped_docs += 1
            return

        doc_type_label = str(payload.get("doc_type") or payload.get("doc_type_template") or "General Document")
        document_type_id = self._get_or_create_document_type(cur, doc_type_label)

        fields = payload.get("fields") or {}
        if not isinstance(fields, dict):
            fields = {}

        property_id = self._get_or_create_property(cur, client_id, fields)
        tenant_id = self._get_or_create_tenant(cur, client_id, property_id, doc_type_label, fields)
        if property_id:
            self.stats.properties_linked += 1
        if tenant_id:
            self.stats.tenants_linked += 1

        review = payload.get("review") or {}
        pdf_ref = (payload.get("files") or {}).get("pdf") or _find_pdf_name(doc_folder)
        raw_image_ref = (payload.get("files") or {}).get("raw_image") or _find_raw_image_name(doc_folder)

        pdf_path = str((doc_folder / pdf_ref).resolve()) if pdf_ref else None
        raw_image_path = str((doc_folder / raw_image_ref).resolve()) if raw_image_ref else None

        full_text = None
        if isinstance(payload.get("full_text"), str):
            full_text = payload["full_text"]

        batch_date = _parse_date(date_folder.name)

        cur.execute(
            """
            INSERT INTO documents (
                client_id, property_id, document_type_id, source_doc_id, doc_name, status,
                pdf_path, raw_image_path, full_text, quality_score,
                reviewed_by, reviewed_at, scanned_at, exported_at, batch_date
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            ON CONFLICT (client_id, source_doc_id)
            DO UPDATE SET
                property_id = EXCLUDED.property_id,
                document_type_id = EXCLUDED.document_type_id,
                doc_name = EXCLUDED.doc_name,
                status = EXCLUDED.status,
                pdf_path = EXCLUDED.pdf_path,
                raw_image_path = EXCLUDED.raw_image_path,
                full_text = COALESCE(EXCLUDED.full_text, documents.full_text),
                quality_score = EXCLUDED.quality_score,
                reviewed_by = EXCLUDED.reviewed_by,
                reviewed_at = EXCLUDED.reviewed_at,
                scanned_at = EXCLUDED.scanned_at,
                exported_at = EXCLUDED.exported_at,
                batch_date = EXCLUDED.batch_date
            RETURNING id, (xmax = 0) AS inserted
            """,
            (
                client_id,
                property_id,
                document_type_id,
                source_doc_id,
                payload.get("doc_name"),
                payload.get("status") or "New",
                pdf_path,
                raw_image_path,
                full_text,
                payload.get("quality_score"),
                review.get("reviewed_by"),
                _parse_datetime(review.get("reviewed_at")),
                _parse_datetime(review.get("scanned_at")),
                _parse_datetime(review.get("exported_at")),
                batch_date,
            ),
        )
        doc_row = cur.fetchone()
        document_id = int(doc_row["id"])

        if doc_row["inserted"]:
            self.stats.imported_docs += 1
        else:
            self.stats.updated_docs += 1

        self._upsert_fields(cur, document_id, fields)
        self._upsert_compliance(cur, client_id, property_id, document_id, fields)

    def _get_or_create_document_type(self, cur, label: str) -> int:
        key = _slugify(label).replace("-", "_")

        cur.execute("SELECT id FROM document_types WHERE key = %s", (key,))
        row = cur.fetchone()
        if row:
            return int(row["id"])

        has_expiry, expiry_field_key = _infer_expiry_rule(label)
        cur.execute(
            """
            INSERT INTO document_types (key, label, has_expiry, expiry_field_key, is_active)
            VALUES (%s, %s, %s, %s, TRUE)
            RETURNING id
            """,
            (key, label, has_expiry, expiry_field_key),
        )
        return int(cur.fetchone()["id"])

    def _get_or_create_property(self, cur, client_id: int, fields: dict[str, Any]) -> int | None:
        address = (fields.get("property_address") or "").strip()
        if not address:
            return None

        cur.execute(
            """
            INSERT INTO properties (client_id, address)
            VALUES (%s, %s)
            ON CONFLICT (client_id, address)
            DO UPDATE SET address = EXCLUDED.address
            RETURNING id
            """,
            (client_id, address),
        )
        return int(cur.fetchone()["id"])

    def _get_or_create_tenant(
        self,
        cur,
        client_id: int,
        property_id: int | None,
        doc_type_label: str,
        fields: dict[str, Any],
    ) -> int | None:
        if doc_type_label.strip().lower() not in TENANCY_DOC_TYPES:
            return None

        tenant_name = (fields.get("tenant_full_name") or "").strip()
        if not tenant_name:
            return None

        tenancy_start = _parse_date(fields.get("start_date"))
        tenancy_end = _parse_date(fields.get("end_date"))

        cur.execute(
            """
            INSERT INTO tenants (client_id, property_id, full_name, tenancy_start, tenancy_end)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (client_id, property_id, full_name)
            DO UPDATE SET
                tenancy_start = COALESCE(EXCLUDED.tenancy_start, tenants.tenancy_start),
                tenancy_end = COALESCE(EXCLUDED.tenancy_end, tenants.tenancy_end)
            RETURNING id
            """,
            (client_id, property_id, tenant_name, tenancy_start, tenancy_end),
        )
        return int(cur.fetchone()["id"])

    def _upsert_fields(self, cur, document_id: int, fields: dict[str, Any]) -> None:
        for key, value in fields.items():
            field_key = str(key)
            field_value = "" if value is None else str(value)
            field_label = _field_label_from_key(field_key)

            cur.execute(
                """
                INSERT INTO document_fields (document_id, field_key, field_label, field_value, source)
                VALUES (%s, %s, %s, %s, 'review_json')
                ON CONFLICT (document_id, field_key)
                DO UPDATE SET
                    field_label = EXCLUDED.field_label,
                    field_value = EXCLUDED.field_value,
                    source = EXCLUDED.source,
                    updated_at = NOW()
                """,
                (document_id, field_key, field_label, field_value),
            )
            self.stats.field_rows += 1

    def _upsert_compliance(
        self,
        cur,
        client_id: int,
        property_id: int | None,
        document_id: int,
        fields: dict[str, Any],
    ) -> None:
        for record_type, field_key in (
            ("gas_safety_expiry", "expiry_date"),
            ("eicr_due", "next_inspection_date"),
            ("epc_expiry", "valid_until"),
            ("tenancy_end", "end_date"),
        ):
            raw_value = fields.get(field_key)
            expiry = _parse_date(raw_value)
            if not expiry:
                continue
            status = _compliance_status(expiry)

            cur.execute(
                """
                INSERT INTO compliance_records (
                    client_id, property_id, document_id, record_type, expiry_date, status, details
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (document_id, record_type)
                DO UPDATE SET
                    property_id = EXCLUDED.property_id,
                    expiry_date = EXCLUDED.expiry_date,
                    status = EXCLUDED.status,
                    details = EXCLUDED.details,
                    updated_at = NOW()
                """,
                (client_id, property_id, document_id, record_type, expiry, status, f"From field: {field_key}"),
            )


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _slugify(value: str) -> str:
    base = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in base:
        base = base.replace("--", "-")
    return base.strip("-") or "client"


def _parse_datetime(raw: Any) -> datetime | None:
    if not raw or not isinstance(raw, str):
        return None
    text = raw.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
    return None


def _parse_date(raw: Any) -> date | None:
    if not raw:
        return None
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()

    text = str(raw).strip()
    if not text:
        return None

    for parser in (
        lambda t: datetime.fromisoformat(t).date(),
        lambda t: datetime.strptime(t, "%d/%m/%Y").date(),
        lambda t: datetime.strptime(t, "%Y-%m-%d").date(),
        lambda t: datetime.strptime(t, "%d-%m-%Y").date(),
    ):
        try:
            return parser(text)
        except ValueError:
            continue
    return None


def _find_pdf_name(doc_folder: Path) -> str | None:
    for child in sorted(doc_folder.iterdir()):
        if child.is_file() and child.suffix.lower() == ".pdf":
            return child.name
    return None


def _find_raw_image_name(doc_folder: Path) -> str | None:
    for child in sorted(doc_folder.iterdir()):
        if child.is_file() and child.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
            return child.name
    return None


def _field_label_from_key(key: str) -> str:
    return key.replace("_", " ").strip().title()


def _infer_expiry_rule(doc_type_label: str) -> tuple[bool, str | None]:
    label = doc_type_label.lower()
    if "gas" in label:
        return True, "expiry_date"
    if "eicr" in label:
        return True, "next_inspection_date"
    if "epc" in label:
        return True, "valid_until"
    if "tenancy" in label:
        return True, "end_date"
    return False, None


def _compliance_status(expiry_date: date) -> str:
    today = date.today()
    delta = (expiry_date - today).days
    if delta < 0:
        return "expired"
    if delta <= 30:
        return "expiring_soon"
    return "valid"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import ScanSystem DOC folders into portal DB")
    parser.add_argument("--dsn", default=os.getenv("DATABASE_URL"), help="PostgreSQL DSN (or set DATABASE_URL)")
    parser.add_argument("--client-name", required=True, help="Portal client name (agency)")
    parser.add_argument(
        "--client-root",
        required=True,
        help="Path to existing client folder, e.g. C:/ScanSystem_v2/Clients/Belvoir Harlow",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    if not args.dsn:
        parser.error("--dsn not provided and DATABASE_URL is not set")

    importer = FilesystemImporter(
        dsn=args.dsn,
        client_name=args.client_name,
        client_root=Path(args.client_root),
    )
    stats = importer.run()

    print("Import complete")
    print(f"Scanned docs: {stats.scanned_docs}")
    print(f"Inserted docs: {stats.imported_docs}")
    print(f"Updated docs: {stats.updated_docs}")
    print(f"Skipped docs: {stats.skipped_docs}")
    print(f"Field upserts: {stats.field_rows}")
    print(f"Property links: {stats.properties_linked}")
    print(f"Tenant links: {stats.tenants_linked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
