from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


PRODUCT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PRODUCT_ROOT / "portal.db"
OLD_PRODUCT_ROOT = Path(r"C:\Users\user\OneDrive - University of East London\Desktop\MorphIQ\Product")
NEW_PRODUCT_ROOT = PRODUCT_ROOT


@dataclass
class DocRow:
    id: int
    client_id: int
    property_id: int | None
    source_doc_id: str
    doc_name: str
    status: str
    pdf_path: str | None
    raw_image_path: str | None
    imported_at: str | None
    deleted_at: str | None
    document_type_id: int | None
    doc_key: str | None


def remap_path(path_str: str | None) -> str | None:
    if not path_str:
        return path_str
    path = Path(path_str)
    try:
        relative = path.relative_to(OLD_PRODUCT_ROOT)
    except ValueError:
        return path_str
    candidate = NEW_PRODUCT_ROOT / relative
    return str(candidate) if candidate.exists() else path_str


def normalize_text(*values: str | None) -> str:
    text = " ".join(v or "" for v in values).lower()
    return (
        text.replace("-", " ")
        .replace("_", " ")
        .replace(".jpg", " ")
        .replace(".jpeg", " ")
        .replace(".pdf", " ")
    )


def infer_supported_key(doc_name: str | None, pdf_path: str | None, source_doc_id: str | None) -> str | None:
    text = normalize_text(doc_name, pdf_path, source_doc_id)

    if "inventory" in text:
        return "inventory"
    if "deposit cert" in text or "deposit protection" in text or "deposit" in text:
        return "deposit-protection-certificate"
    if "gas safety" in text or "cp12" in text:
        return "gas-safety-certificate"
    if "eicr" in text:
        return "eicr"
    if "epc" in text:
        return "epc"
    if "tenancy agreement" in text or "tenancy" in text or "ast" in text:
        return "tenancy-agreement"
    return None


def doc_folder_for(pdf_path: str | None) -> Path | None:
    if not pdf_path:
        return None
    path = Path(remap_path(pdf_path))
    return path.parent if path.parent.exists() else None


def has_bulk_marker(doc_folder: Path | None) -> bool:
    if not doc_folder:
        return False
    if (doc_folder / ".bulk_import.json").exists():
        return True
    try:
        client_dir = doc_folder.parents[2]
    except IndexError:
        return False
    return (client_dir / ".bulk_import.json").exists()


def keep_rank(row: DocRow) -> tuple[int, int, str, int]:
    resolved_pdf = remap_path(row.pdf_path)
    file_exists = int(bool(resolved_pdf and Path(resolved_pdf).exists()))
    imported_at = row.imported_at or ""
    source_is_doc = int((row.source_doc_id or "").startswith("DOC-"))
    return (file_exists, source_is_doc, imported_at, row.id)


def timestamp_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    type_rows = list(cur.execute("SELECT id, key FROM document_types"))
    type_id_by_key = {row["key"]: row["id"] for row in type_rows}
    canonical_deposit_id = type_id_by_key["deposit-protection-certificate"]
    legacy_deposit_id = type_id_by_key.get("deposit-protection")
    unknown_id = type_id_by_key["unknown"]

    path_updates = 0
    deposit_remaps = 0
    unknown_reclassified = 0
    unknown_deleted = 0
    duplicates_deleted = 0

    all_docs = []
    for row in cur.execute(
        """
        SELECT d.id, d.client_id, d.property_id, d.source_doc_id, d.doc_name, d.status,
               d.pdf_path, d.raw_image_path, d.imported_at, d.deleted_at,
               d.document_type_id, dt.key AS doc_key
        FROM documents d
        LEFT JOIN document_types dt ON dt.id = d.document_type_id
        ORDER BY d.id
        """
    ):
        all_docs.append(
            DocRow(
                id=row["id"],
                client_id=row["client_id"],
                property_id=row["property_id"],
                source_doc_id=row["source_doc_id"] or "",
                doc_name=row["doc_name"] or "",
                status=row["status"] or "",
                pdf_path=row["pdf_path"],
                raw_image_path=row["raw_image_path"],
                imported_at=row["imported_at"],
                deleted_at=row["deleted_at"],
                document_type_id=row["document_type_id"],
                doc_key=row["doc_key"],
            )
        )

    for row in all_docs:
        new_pdf_path = remap_path(row.pdf_path)
        new_raw_path = remap_path(row.raw_image_path)
        if new_pdf_path != row.pdf_path or new_raw_path != row.raw_image_path:
            cur.execute(
                "UPDATE documents SET pdf_path = ?, raw_image_path = ? WHERE id = ?",
                (new_pdf_path, new_raw_path, row.id),
            )
            row.pdf_path = new_pdf_path
            row.raw_image_path = new_raw_path
            path_updates += 1

        if row.document_type_id == legacy_deposit_id:
            cur.execute(
                "UPDATE documents SET document_type_id = ? WHERE id = ?",
                (canonical_deposit_id, row.id),
            )
            row.document_type_id = canonical_deposit_id
            row.doc_key = "deposit-protection-certificate"
            deposit_remaps += 1

        if row.deleted_at is not None:
            continue

        if row.document_type_id == unknown_id:
            inferred_key = infer_supported_key(row.doc_name, row.pdf_path, row.source_doc_id)
            if inferred_key:
                cur.execute(
                    "UPDATE documents SET document_type_id = ? WHERE id = ?",
                    (type_id_by_key[inferred_key], row.id),
                )
                row.document_type_id = type_id_by_key[inferred_key]
                row.doc_key = inferred_key
                unknown_reclassified += 1
            else:
                folder = doc_folder_for(row.pdf_path)
                if row.status == "new" and has_bulk_marker(folder):
                    cur.execute(
                        "UPDATE documents SET deleted_at = ? WHERE id = ?",
                        (timestamp_now(), row.id),
                    )
                    row.deleted_at = timestamp_now()
                    unknown_deleted += 1

    active_groups: dict[tuple[int | None, str | None], list[DocRow]] = defaultdict(list)
    for row in all_docs:
        if row.deleted_at is None:
            active_groups[(row.property_id, row.doc_key)].append(row)

    for (property_id, doc_key), rows in active_groups.items():
        if property_id is None or doc_key is None or len(rows) < 2:
            continue
        if doc_key == "unknown":
            continue
        keep = max(rows, key=keep_rank)
        for row in rows:
            if row.id == keep.id:
                continue
            cur.execute(
                "UPDATE documents SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
                (timestamp_now(), row.id),
            )
            duplicates_deleted += cur.rowcount
            row.deleted_at = timestamp_now()

    conn.commit()

    print(
        {
            "path_updates": path_updates,
            "deposit_remaps": deposit_remaps,
            "unknown_reclassified": unknown_reclassified,
            "unknown_deleted": unknown_deleted,
            "duplicates_deleted": duplicates_deleted,
        }
    )

    print("\nPOST_CLEANUP_COUNTS")
    for row in cur.execute(
        """
        SELECT dt.key, COUNT(*) AS c
        FROM documents d
        LEFT JOIN document_types dt ON dt.id = d.document_type_id
        WHERE d.deleted_at IS NULL
        GROUP BY dt.key
        ORDER BY c DESC, dt.key
        """
    ):
        print(f"{row['key']}\t{row['c']}")

    print("\nACTIVE_UNKNOWN_DOCS")
    for row in cur.execute(
        """
        SELECT d.id, d.source_doc_id, d.doc_name, p.address, d.pdf_path
        FROM documents d
        LEFT JOIN document_types dt ON dt.id = d.document_type_id
        LEFT JOIN properties p ON p.id = d.property_id
        WHERE d.deleted_at IS NULL AND dt.key = 'unknown'
        ORDER BY d.id
        """
    ):
        print(dict(row))

    conn.close()


if __name__ == "__main__":
    main()
