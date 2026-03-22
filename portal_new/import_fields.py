"""
MorphIQ — Import Fields from review.json into SQLite
Walks the Clients folder, finds review.json files, and populates
the document_fields table in portal.db.

Usage:
    cd C:\ScanSystem_v2
    python portal_new\import_fields.py

This is safe to run multiple times — it skips fields that already exist.
"""

import os
import json
import sqlite3
import sys

# ── Config ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, "..")
DB_PATH = os.path.join(PROJECT_ROOT, "portal.db")
CLIENTS_DIR = os.path.join(PROJECT_ROOT, "Clients")


def find_review_jsons(clients_dir):
    """Walk the Clients folder and find all review.json files."""
    results = []
    if not os.path.isdir(clients_dir):
        print(f"  Clients directory not found: {clients_dir}")
        return results

    for root, dirs, files in os.walk(clients_dir):
        if "review.json" in files:
            results.append(os.path.join(root, "review.json"))
    return results


def import_fields(db_path, review_jsons):
    """Read each review.json, match to a document in the DB, and insert fields."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    imported = 0
    skipped = 0
    not_found = 0

    for path in review_jsons:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  SKIP (bad file): {path} — {e}")
            skipped += 1
            continue

        doc_id = data.get("doc_id", "")
        fields = data.get("fields", {})
        status = data.get("status", "")

        if not doc_id:
            print(f"  SKIP (no doc_id): {path}")
            skipped += 1
            continue

        # Find matching document in DB
        cur.execute("SELECT id FROM documents WHERE source_doc_id = ?", (doc_id,))
        row = cur.fetchone()
        if not row:
            print(f"  NOT FOUND in DB: {doc_id} — {path}")
            not_found += 1
            continue

        document_id = row["id"]

        # Update document status if review.json has a status
        if status:
            cur.execute(
                "UPDATE documents SET status = ? WHERE id = ?",
                (status.lower().replace(" ", "_"), document_id),
            )

        # Update reviewed_by and reviewed_at if present
        review = data.get("review", {})
        if review.get("reviewed_by"):
            cur.execute(
                "UPDATE documents SET reviewed_by = ?, reviewed_at = ? WHERE id = ?",
                (review.get("reviewed_by", ""), review.get("reviewed_at", ""), document_id),
            )

        # Insert fields (skip if already exist)
        for key, value in fields.items():
            if not value:  # Skip empty fields
                continue

            # Check if field already exists
            cur.execute(
                "SELECT id FROM document_fields WHERE document_id = ? AND field_key = ?",
                (document_id, key),
            )
            if cur.fetchone():
                continue  # Already imported

            label = key.replace("_", " ").title()
            cur.execute(
                """INSERT INTO document_fields 
                   (document_id, field_key, field_label, field_value, source) 
                   VALUES (?, ?, ?, ?, 'review_json')""",
                (document_id, key, label, str(value)),
            )
            imported += 1

    conn.commit()
    conn.close()

    return imported, skipped, not_found


def main():
    print(f"\nMorphIQ — Import Fields from review.json")
    print(f"{'='*50}")
    print(f"  Database: {DB_PATH}")
    print(f"  Clients:  {CLIENTS_DIR}")
    print()

    if not os.path.isfile(DB_PATH):
        print(f"  ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    # Find all review.json files
    review_jsons = find_review_jsons(CLIENTS_DIR)
    print(f"  Found {len(review_jsons)} review.json file(s)")

    if not review_jsons:
        print("  Nothing to import.")
        return

    for path in review_jsons:
        print(f"    {path}")

    print()

    # Import
    imported, skipped, not_found = import_fields(DB_PATH, review_jsons)

    print(f"\n  Results:")
    print(f"    Fields imported: {imported}")
    print(f"    Files skipped:   {skipped}")
    print(f"    Docs not in DB:  {not_found}")
    print()


if __name__ == "__main__":
    main()
