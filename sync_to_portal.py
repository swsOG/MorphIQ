"""
MorphIQ — Sync Pipeline to Portal
Walks the Clients folder, reads every review.json, and syncs
documents + fields into portal.db.

Usage:
    cd <project_root>
    python sync_to_portal.py

Safe to run multiple times — updates existing records, inserts new ones.
"""

import os
import json
import sqlite3
import sys
from datetime import datetime

# ── Config ───────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "portal.db")
CLIENTS_DIR = os.path.join(SCRIPT_DIR, "Clients")

# Map review.json doc_type values to document_types.key in the DB
DOC_TYPE_MAP = {
    "Tenancy Agreement": "tenancy-agreement",
    "Gas Safety Certificate": "gas-safety-certificate",
    "EICR": "eicr",
    "EPC": "epc",
    "Deposit Protection": "deposit-protection",
    "Inventory": "inventory",
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_client(conn, client_name):
    """Get or create a client. Returns client_id."""
    slug = client_name.lower().replace(" ", "-")
    row = conn.execute(
        "SELECT id FROM clients WHERE slug = ?", (slug,)
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO clients (name, slug, is_active) VALUES (?, ?, 1)",
        (client_name, slug),
    )
    conn.commit()
    print(f"  + Created client: {client_name}")
    return cur.lastrowid


def ensure_document_type(conn, doc_type_label):
    """Get or create a document type. Returns document_type_id."""
    key = DOC_TYPE_MAP.get(doc_type_label, doc_type_label.lower().replace(" ", "-"))
    row = conn.execute(
        "SELECT id FROM document_types WHERE key = ?", (key,)
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO document_types (key, label, is_active) VALUES (?, ?, 1)",
        (key, doc_type_label),
    )
    conn.commit()
    print(f"  + Created document type: {doc_type_label} ({key})")
    return cur.lastrowid


def ensure_property(conn, client_id, address):
    """Get or create a property by address. Returns property_id."""
    if not address or address.strip() == "":
        # Use or create a placeholder
        row = conn.execute(
            "SELECT id FROM properties WHERE client_id = ? AND address = 'Unassigned property'",
            (client_id,),
        ).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO properties (client_id, address) VALUES (?, 'Unassigned property')",
            (client_id,),
        )
        conn.commit()
        return cur.lastrowid

    # Extract postcode (last part that looks like a UK postcode)
    parts = address.strip().split(",")
    postcode = parts[-1].strip() if len(parts) > 1 else None

    row = conn.execute(
        "SELECT id FROM properties WHERE client_id = ? AND address = ?",
        (client_id, address.strip()),
    ).fetchone()
    if row:
        return row["id"]

    cur = conn.execute(
        "INSERT INTO properties (client_id, address, postcode) VALUES (?, ?, ?)",
        (client_id, address.strip(), postcode),
    )
    conn.commit()
    print(f"  + Created property: {address.strip()}")
    return cur.lastrowid


def sync_document(conn, client_id, property_id, doc_type_id, review_data, doc_folder, batch_date):
    """Insert or update a document record. Returns document_id."""
    doc_id = review_data.get("doc_id", "")
    if not doc_id:
        return None

    files = review_data.get("files", {})
    review = review_data.get("review", {})

    # Build absolute paths
    pdf_filename = files.get("pdf", "")
    raw_filename = files.get("raw_image", "")
    pdf_path = os.path.join(doc_folder, pdf_filename) if pdf_filename else ""
    raw_path = os.path.join(doc_folder, raw_filename) if raw_filename else ""

    # Map status
    status_raw = review_data.get("status", "new")
    status_map = {
        "ai_prefilled": "ai_prefilled",
        "ai-prefilled": "ai_prefilled",
        "verified": "verified",
        "Verified": "verified",
        "needs_review": "needs_review",
        "Needs Review": "needs_review",
        "failed": "failed",
        "Failed": "failed",
        "new": "new",
        "New": "new",
    }
    status = status_map.get(status_raw, status_raw.lower())

    # Check if document already exists
    existing = conn.execute(
        "SELECT id FROM documents WHERE source_doc_id = ? AND client_id = ?",
        (doc_id, client_id),
    ).fetchone()

    if existing:
        # Update existing record
        conn.execute(
            """UPDATE documents SET
                property_id = ?,
                document_type_id = ?,
                doc_name = ?,
                status = ?,
                pdf_path = ?,
                raw_image_path = ?,
                quality_score = ?,
                reviewed_by = ?,
                reviewed_at = ?,
                scanned_at = ?,
                batch_date = ?
            WHERE id = ?""",
            (
                property_id,
                doc_type_id,
                review_data.get("doc_name", ""),
                status,
                pdf_path,
                raw_path,
                review_data.get("quality_score", ""),
                review.get("reviewed_by", ""),
                review.get("reviewed_at", ""),
                review.get("scanned_at", ""),
                batch_date,
                existing["id"],
            ),
        )
        return existing["id"]
    else:
        # Insert new record
        cur = conn.execute(
            """INSERT INTO documents
                (client_id, property_id, document_type_id, source_doc_id,
                 doc_name, status, pdf_path, raw_image_path, quality_score,
                 reviewed_by, reviewed_at, scanned_at, batch_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                client_id,
                property_id,
                doc_type_id,
                doc_id,
                review_data.get("doc_name", ""),
                status,
                pdf_path,
                raw_path,
                review_data.get("quality_score", ""),
                review.get("reviewed_by", ""),
                review.get("reviewed_at", ""),
                review.get("scanned_at", ""),
                batch_date,
            ),
        )
        return cur.lastrowid


def sync_fields(conn, document_id, fields):
    """Insert or update document fields."""
    if not fields:
        return 0

    count = 0
    for key, value in fields.items():
        if not value or str(value).strip() == "":
            continue

        label = key.replace("_", " ").title()

        existing = conn.execute(
            "SELECT id FROM document_fields WHERE document_id = ? AND field_key = ?",
            (document_id, key),
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE document_fields
                   SET field_value = ?, field_label = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (str(value), label, existing["id"]),
            )
        else:
            conn.execute(
                """INSERT INTO document_fields
                   (document_id, field_key, field_label, field_value, source)
                   VALUES (?, ?, ?, ?, 'review_json')""",
                (document_id, key, label, str(value)),
            )
            count += 1

    return count


def cleanup_empty_properties(conn):
    """Delete properties that have no documents linked to them."""
    cur = conn.cursor()
    cur.execute(
        """
           DELETE FROM properties 
           WHERE id NOT IN (
               SELECT DISTINCT property_id FROM documents WHERE property_id IS NOT NULL
           )
       """
    )
    deleted = cur.rowcount
    if deleted > 0:
        conn.commit()
        print(f"Cleaned up {deleted} empty properties")
    return deleted


def find_all_doc_folders(clients_dir):
    """
    Walk the Clients folder and find all DOC-XXXXX folders with review.json.
    Returns list of (client_name, batch_date, doc_folder_path).
    """
    results = []

    if not os.path.isdir(clients_dir):
        print(f"  ERROR: Clients directory not found: {clients_dir}")
        return results

    for client_name in os.listdir(clients_dir):
        client_path = os.path.join(clients_dir, client_name)
        if not os.path.isdir(client_path):
            continue

        batches_path = os.path.join(client_path, "Batches")
        if not os.path.isdir(batches_path):
            continue

        for batch_date in os.listdir(batches_path):
            batch_path = os.path.join(batches_path, batch_date)
            if not os.path.isdir(batch_path):
                continue

            for doc_folder_name in os.listdir(batch_path):
                if not doc_folder_name.startswith("DOC-"):
                    continue

                doc_folder = os.path.join(batch_path, doc_folder_name)
                review_path = os.path.join(doc_folder, "review.json")

                if os.path.isfile(review_path):
                    results.append((client_name, batch_date, doc_folder))

    return results


def sync_portal_for_clients(target_clients=None):
    print(f"\n{'='*60}")
    print(f"  MorphIQ — Sync Pipeline to Portal")
    print(f"{'='*60}")
    print(f"  Database: {DB_PATH}")
    print(f"  Clients:  {CLIENTS_DIR}")
    print(f"  Time:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if not os.path.isfile(DB_PATH):
        print(f"  ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    # Find all DOC folders with review.json
    doc_folders = find_all_doc_folders(CLIENTS_DIR)
    if target_clients:
        target_set = set(target_clients)
        doc_folders = [t for t in doc_folders if t[0] in target_set]
    print(f"  Found {len(doc_folders)} document(s) with review.json\n")

    if not doc_folders:
        print("  Nothing to sync.")
        return

    conn = get_db()

    new_docs = 0
    updated_docs = 0
    new_fields = 0
    errors = 0

    # Track which documents actually exist on disk per client so we can
    # remove any stale records from the portal database (e.g. old batches
    # you have deleted from Clients\).
    seen_docs_by_client: dict[str, set[str]] = {}
    client_ids: dict[str, int] = {}

    for client_name, batch_date, doc_folder in doc_folders:
        review_path = os.path.join(doc_folder, "review.json")

        try:
            with open(review_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  ERROR reading {review_path}: {e}")
            errors += 1
            continue

        doc_id = data.get("doc_id", "")
        if not doc_id:
            print(f"  SKIP (no doc_id): {review_path}")
            continue

        # Track that this doc_id exists on disk for this client
        seen_docs_by_client.setdefault(client_name, set()).add(doc_id)

        # Ensure client exists
        client_id = ensure_client(conn, client_name)
        client_ids[client_name] = client_id

        # Ensure document type exists
        doc_type_label = data.get("doc_type", "Unknown")
        doc_type_id = ensure_document_type(conn, doc_type_label)

        # Ensure property exists (from extracted fields)
        fields = data.get("fields", {})
        property_address = fields.get("property_address", "")
        property_id = ensure_property(conn, client_id, property_address)

        # Check if this is new or update
        existing = conn.execute(
            "SELECT id FROM documents WHERE source_doc_id = ? AND client_id = ?",
            (doc_id, client_id),
        ).fetchone()
        is_new = existing is None

        # Sync document
        document_id = sync_document(
            conn, client_id, property_id, doc_type_id,
            data, doc_folder, batch_date
        )

        if document_id is None:
            continue

        if is_new:
            new_docs += 1
        else:
            updated_docs += 1

        # Sync fields
        field_count = sync_fields(conn, document_id, fields)
        new_fields += field_count

        status_icon = "+" if is_new else "~"
        print(f"  {status_icon} {doc_id} | {client_name} | {doc_type_label} | {data.get('status', '?')} | {field_count} fields")

    # After syncing all documents that currently exist on disk, remove any
    # portal records that point at DOC folders which no longer exist.
    for client_name, client_id in client_ids.items():
        existing_ids = seen_docs_by_client.get(client_name, set())
        if not existing_ids:
            continue

        placeholders = ",".join("?" for _ in existing_ids)
        try:
            rows = conn.execute(
                f"SELECT id FROM documents WHERE client_id = ? AND source_doc_id NOT IN ({placeholders})",
                (client_id, *existing_ids),
            ).fetchall()
        except sqlite3.OperationalError:
            # If SQLite doesn't like the query for some reason, skip cleanup.
            rows = []

        stale_doc_ids = [row["id"] for row in rows]
        if stale_doc_ids:
            id_placeholders = ",".join("?" for _ in stale_doc_ids)
            conn.execute(
                f"DELETE FROM document_fields WHERE document_id IN ({id_placeholders})",
                stale_doc_ids,
            )
            conn.execute(
                f"DELETE FROM documents WHERE id IN ({id_placeholders})",
                stale_doc_ids,
            )
            print(f"  - Removed {len(stale_doc_ids)} stale document(s) for client {client_name} (DOC folder missing)")

    # Additionally, remove any documents for clients that no longer have a
    # corresponding folder under Clients\. This cleans up old data when an
    # entire client has been deleted from the filesystem.
    try:
        cursor = conn.execute("SELECT id, name FROM clients")
        client_rows = cursor.fetchall()
    except sqlite3.OperationalError:
        client_rows = []

    for row in client_rows:
        c_id = row["id"]
        c_name = row["name"]
        client_dir = os.path.join(CLIENTS_DIR, c_name)
        if not os.path.isdir(client_dir):
            # Delete all documents (and their fields) for this missing client
            doc_ids = [
                r["id"]
                for r in conn.execute(
                    "SELECT id FROM documents WHERE client_id = ?", (c_id,)
                ).fetchall()
            ]
            if doc_ids:
                id_placeholders = ",".join("?" for _ in doc_ids)
                conn.execute(
                    f"DELETE FROM document_fields WHERE document_id IN ({id_placeholders})",
                    doc_ids,
                )
                conn.execute(
                    f"DELETE FROM documents WHERE id IN ({id_placeholders})",
                    doc_ids,
                )
                print(f"  - Removed {len(doc_ids)} document(s) for missing client folder: {c_name}")

    # After all document and client cleanup, remove any properties that are no longer used.
    cleanup_empty_properties(conn)

    conn.commit()
    conn.close()

    print(f"\n{'='*60}")
    print(f"  Results:")
    print(f"    New documents:     {new_docs}")
    print(f"    Updated documents: {updated_docs}")
    print(f"    New fields added:  {new_fields}")
    print(f"    Errors:            {errors}")
    print(f"{'='*60}\n")

    return {
        "new_docs": new_docs,
        "updated_docs": updated_docs,
        "new_fields": new_fields,
        "errors": errors,
    }


def main():
    sync_portal_for_clients()


if __name__ == "__main__":
    main()


def _find_single_doc_folder(client_name: str, doc_id: str):
    """
    Find a single DOC folder for a given client/doc_id.
    Returns (batch_date, doc_folder_path) or (None, None) if not found.
    """
    client_path = os.path.join(CLIENTS_DIR, client_name)
    batches_path = os.path.join(client_path, "Batches")
    if not os.path.isdir(batches_path):
        return None, None

    for batch_date in os.listdir(batches_path):
        batch_path = os.path.join(batches_path, batch_date)
        if not os.path.isdir(batch_path):
            continue

        doc_folder = os.path.join(batch_path, doc_id)
        review_path = os.path.join(doc_folder, "review.json")
        if os.path.isdir(doc_folder) and os.path.isfile(review_path):
            return batch_date, doc_folder

    return None, None


def sync_single_doc(client_name: str, doc_id: str):
    """
    Sync a single document into portal.db based on its review.json.

    - Reads Clients/<client_name>/Batches/*/<doc_id>/review.json
    - Upserts client, property, document_type, document, and document_fields
    - If the property_address changed, removes any now-empty old property row.
    """
    if not os.path.isfile(DB_PATH):
        print(f"[sync_single_doc] SKIP — database not found at {DB_PATH}")
        return

    batch_date, doc_folder = _find_single_doc_folder(client_name, doc_id)
    if not doc_folder:
        print(f"[sync_single_doc] SKIP — review.json not found for {client_name} / {doc_id}")
        return

    review_path = os.path.join(doc_folder, "review.json")
    try:
        with open(review_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[sync_single_doc] ERROR reading {review_path}: {e}")
        return

    source_doc_id = data.get("doc_id") or doc_id
    if not source_doc_id:
        print(f"[sync_single_doc] SKIP — no doc_id in {review_path}")
        return

    fields = data.get("fields", {}) or {}
    property_address = fields.get("property_address", "")
    doc_type_label = data.get("doc_type", "Unknown")

    conn = get_db()
    try:
        # Ensure client, document type, and property
        client_id = ensure_client(conn, client_name)
        doc_type_id = ensure_document_type(conn, doc_type_label)
        property_id = ensure_property(conn, client_id, property_address)

        # Capture old property before updating the document
        existing_row = conn.execute(
            "SELECT id, property_id FROM documents WHERE source_doc_id = ? AND client_id = ?",
            (source_doc_id, client_id),
        ).fetchone()
        old_property_id = existing_row["property_id"] if existing_row else None

        # Upsert the document record
        document_id = sync_document(
            conn,
            client_id,
            property_id,
            doc_type_id,
            data,
            doc_folder,
            batch_date or "",
        )
        if document_id is None:
            print(f"[sync_single_doc] SKIP — could not sync document record for {client_name} / {source_doc_id}")
            return

        # Sync document fields
        field_count = sync_fields(conn, document_id, fields)

        # If property changed, and the old property is now unused, delete it
        if old_property_id and old_property_id != property_id:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM documents WHERE property_id = ?",
                (old_property_id,),
            ).fetchone()
            if row and row["cnt"] == 0:
                conn.execute("DELETE FROM properties WHERE id = ?", (old_property_id,))
                print(f"[sync_single_doc] Deleted empty property id={old_property_id} (no remaining documents)")

        # Global safety-net cleanup: remove any other properties that have become unused.
        cleanup_empty_properties(conn)

        conn.commit()

        status = data.get("status", "?")
        print(
            f"[sync_single_doc] Synced {source_doc_id} | client={client_name} | "
            f"type={doc_type_label} | status={status} | fields={field_count}"
        )
    finally:
        conn.close()
