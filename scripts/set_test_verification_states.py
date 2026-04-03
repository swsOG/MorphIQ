"""
set_test_verification_states.py
================================
Directly writes the "Harlow & Essex Lettings" test client, 6 properties,
and 27 documents into portal.db with the correct compliance dates and
verification states. Bypasses the watcher/OCR/AI pipeline entirely.

Safe to run multiple times — fully idempotent (upserts by address + doc_type).

DO NOT TOUCH: portal_new/, auto_ocr_watch.py, ai_prefill.py, sync_to_portal.py,
or any other existing client data.
"""

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE    = Path(__file__).resolve().parent.parent
DB_PATH = BASE / "portal.db"
CLIENT  = "Harlow & Essex Lettings"

NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ---------------------------------------------------------------------------
# Document type keys  (must match document_types.key in portal.db)
# NOTE: Use "deposit-protection-certificate" to match the existing DB key
#       so the template workaround (deriveDepositFromDocs) applies correctly.
# ---------------------------------------------------------------------------

DT = {
    "gas_safety":        "gas-safety-certificate",
    "eicr":              "eicr",
    "epc":               "epc",
    "deposit_protection":"deposit-protection-certificate",
    "tenancy_agreement": "tenancy-agreement",
    "inventory":         "inventory",
}

DT_LABEL = {
    "gas-safety-certificate":    "Gas Safety Certificate",
    "eicr":                      "EICR",
    "epc":                       "EPC",
    "deposit-protection-certificate": "Deposit Protection Certificate",
    "tenancy-agreement":         "Tenancy Agreement",
    "inventory":                 "Inventory",
}

# Expiry field key that app.py reads per doc_type (from FIELD_PRIORITY_MAP)
EXPIRY_KEY = {
    "gas-safety-certificate":    "expiry_date",
    "eicr":                      "next_inspection_date",
    "epc":                       "valid_until",
    "deposit-protection-certificate": None,   # no expiry
    "tenancy-agreement":         None,
    "inventory":                 None,
}

# ---------------------------------------------------------------------------
# Full scenario:  (source_id, dt_key, status, expiry_iso or None)
# source_id is a stable identifier we use as documents.source_doc_id
# ---------------------------------------------------------------------------

SCENARIO = [
    # ── PROPERTY 1 — 4 Birchwood Close  (all valid, all verified) ────────────
    ("HE-P1-GAS",  "4 Birchwood Close, Harlow, CM17 0PQ",
     DT["gas_safety"],        "verified",    "2027-03-10",
     "Gas Safety Certificate - 4 Birchwood Close",     "prop1_gas_safety.jpg"),

    ("HE-P1-EICR", "4 Birchwood Close, Harlow, CM17 0PQ",
     DT["eicr"],              "verified",    "2029-01-05",
     "EICR - 4 Birchwood Close",                       "prop1_eicr.jpg"),

    ("HE-P1-EPC",  "4 Birchwood Close, Harlow, CM17 0PQ",
     DT["epc"],               "verified",    "2032-06-20",
     "EPC - 4 Birchwood Close",                        "prop1_epc.jpg"),

    ("HE-P1-DEP",  "4 Birchwood Close, Harlow, CM17 0PQ",
     DT["deposit_protection"],"verified",    None,
     "Deposit Protection Certificate - 4 Birchwood Close", "prop1_deposit.jpg"),

    ("HE-P1-AST",  "4 Birchwood Close, Harlow, CM17 0PQ",
     DT["tenancy_agreement"], "verified",    None,
     "Tenancy Agreement - 4 Birchwood Close",          "prop1_tenancy.jpg"),

    ("HE-P1-INV",  "4 Birchwood Close, Harlow, CM17 0PQ",
     DT["inventory"],         "verified",    None,
     "Inventory Check-in Report - 4 Birchwood Close",  "prop1_inventory.jpg"),

    # ── PROPERTY 2 — 12 Rosebank Avenue  (all expiring, all verified) ────────
    ("HE-P2-GAS",  "12 Rosebank Avenue, Epping, CM16 5TR",
     DT["gas_safety"],        "verified",    "2026-04-18",
     "Gas Safety Certificate - 12 Rosebank Avenue",    "prop2_gas_safety.jpg"),

    ("HE-P2-EICR", "12 Rosebank Avenue, Epping, CM16 5TR",
     DT["eicr"],              "verified",    "2026-05-12",
     "EICR - 12 Rosebank Avenue",                      "prop2_eicr.jpg"),

    ("HE-P2-EPC",  "12 Rosebank Avenue, Epping, CM16 5TR",
     DT["epc"],               "verified",    "2026-06-01",
     "EPC - 12 Rosebank Avenue",                       "prop2_epc.jpg"),

    ("HE-P2-DEP",  "12 Rosebank Avenue, Epping, CM16 5TR",
     DT["deposit_protection"],"verified",    None,
     "Deposit Protection Certificate - 12 Rosebank Avenue", "prop2_deposit.jpg"),

    ("HE-P2-AST",  "12 Rosebank Avenue, Epping, CM16 5TR",
     DT["tenancy_agreement"], "verified",    None,
     "Tenancy Agreement - 12 Rosebank Avenue",         "prop2_tenancy.jpg"),

    # ── PROPERTY 3 — 7 Thornfield Road  (all expired, all verified) ──────────
    ("HE-P3-GAS",  "7 Thornfield Road, Harlow, CM20 2BX",
     DT["gas_safety"],        "verified",    "2025-01-08",
     "Gas Safety Certificate - 7 Thornfield Road",     "prop3_gas_safety.jpg"),

    ("HE-P3-EICR", "7 Thornfield Road, Harlow, CM20 2BX",
     DT["eicr"],              "verified",    "2024-03-15",
     "EICR - 7 Thornfield Road",                       "prop3_eicr.jpg"),

    ("HE-P3-EPC",  "7 Thornfield Road, Harlow, CM20 2BX",
     DT["epc"],               "verified",    "2024-06-02",
     "EPC - 7 Thornfield Road",                        "prop3_epc.jpg"),

    ("HE-P3-AST",  "7 Thornfield Road, Harlow, CM20 2BX",
     DT["tenancy_agreement"], "verified",    None,
     "Tenancy Agreement - 7 Thornfield Road",          "prop3_tenancy.jpg"),

    # ── PROPERTY 4 — 23 Linnet Drive  (mixed, NO deposit) ────────────────────
    ("HE-P4-GAS",  "23 Linnet Drive, Hoddesdon, EN11 9QR",
     DT["gas_safety"],        "verified",    "2027-02-14",
     "Gas Safety Certificate - 23 Linnet Drive",       "prop4_gas_safety.jpg"),

    ("HE-P4-EICR", "23 Linnet Drive, Hoddesdon, EN11 9QR",
     DT["eicr"],              "ai_prefilled","2028-10-03",
     "EICR - 23 Linnet Drive",                         "prop4_eicr.jpg"),

    ("HE-P4-EPC",  "23 Linnet Drive, Hoddesdon, EN11 9QR",
     DT["epc"],               "verified",    "2023-11-05",    # expired
     "EPC - 23 Linnet Drive",                          "prop4_epc.jpg"),

    ("HE-P4-AST",  "23 Linnet Drive, Hoddesdon, EN11 9QR",
     DT["tenancy_agreement"], "verified",    None,
     "Tenancy Agreement - 23 Linnet Drive",            "prop4_tenancy.jpg"),

    # ── PROPERTY 5 — 9 Coppice Lane  (sparse: gas + AST only) ───────────────
    ("HE-P5-GAS",  "9 Coppice Lane, Bishops Stortford, CM23 4HH",
     DT["gas_safety"],        "verified",    "2027-01-22",
     "Gas Safety Certificate - 9 Coppice Lane",        "prop5_gas_safety.jpg"),

    ("HE-P5-AST",  "9 Coppice Lane, Bishops Stortford, CM23 4HH",
     DT["tenancy_agreement"], "ai_prefilled",None,
     "Tenancy Agreement - 9 Coppice Lane",             "prop5_tenancy.jpg"),

    # ── PROPERTY 6 — 31 Mallard Way  (all AI prefilled) ──────────────────────
    ("HE-P6-GAS",  "31 Mallard Way, Epping, CM16 7RN",
     DT["gas_safety"],        "ai_prefilled","2026-07-15",
     "Gas Safety Certificate - 31 Mallard Way",        "prop6_gas_safety.jpg"),

    ("HE-P6-EICR", "31 Mallard Way, Epping, CM16 7RN",
     DT["eicr"],              "ai_prefilled","2028-08-08",
     "EICR - 31 Mallard Way",                          "prop6_eicr.jpg"),

    ("HE-P6-EPC",  "31 Mallard Way, Epping, CM16 7RN",
     DT["epc"],               "ai_prefilled","2033-08-10",
     "EPC - 31 Mallard Way",                           "prop6_epc.jpg"),

    ("HE-P6-DEP",  "31 Mallard Way, Epping, CM16 7RN",
     DT["deposit_protection"],"ai_prefilled",None,
     "Deposit Protection Certificate - 31 Mallard Way","prop6_deposit.jpg"),

    ("HE-P6-AST",  "31 Mallard Way, Epping, CM16 7RN",
     DT["tenancy_agreement"], "ai_prefilled",None,
     "Tenancy Agreement - 31 Mallard Way",             "prop6_tenancy.jpg"),

    ("HE-P6-INV",  "31 Mallard Way, Epping, CM16 7RN",
     DT["inventory"],         "ai_prefilled",None,
     "Inventory Check-in Report - 31 Mallard Way",     "prop6_inventory.jpg"),
]

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_client(conn):
    slug = CLIENT.lower().replace(" ", "-")
    row = conn.execute("SELECT id FROM clients WHERE slug=?", (slug,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO clients (name, slug, is_active) VALUES (?,?,1)",
        (CLIENT, slug),
    )
    print(f"  + Created client: {CLIENT}")
    return cur.lastrowid


def ensure_property(conn, client_id, address):
    row = conn.execute(
        "SELECT id FROM properties WHERE client_id=? AND address=?",
        (client_id, address),
    ).fetchone()
    if row:
        return row["id"]
    parts = address.split(",")
    postcode = parts[-1].strip() if len(parts) > 1 else None
    cur = conn.execute(
        "INSERT INTO properties (client_id, address, postcode) VALUES (?,?,?)",
        (client_id, address, postcode),
    )
    print(f"  + Created property: {address}")
    return cur.lastrowid


def ensure_document_type(conn, dt_key):
    row = conn.execute(
        "SELECT id FROM document_types WHERE key=?", (dt_key,)
    ).fetchone()
    if row:
        return row["id"]
    label = DT_LABEL.get(dt_key, dt_key.replace("-", " ").title())
    cur = conn.execute(
        "INSERT INTO document_types (key, label, is_active) VALUES (?,?,1)",
        (dt_key, label),
    )
    print(f"  + Created document type: {dt_key}")
    return cur.lastrowid


def upsert_document(conn, client_id, property_id, dt_id, source_id,
                    doc_name, status, jpg_name):
    reviewed_at = NOW if status == "verified" else ""
    reviewed_by = "test-setup" if status == "verified" else ""

    row = conn.execute(
        "SELECT id FROM documents WHERE source_doc_id=? AND client_id=?",
        (source_id, client_id),
    ).fetchone()

    if row:
        conn.execute(
            """UPDATE documents SET
               property_id=?, document_type_id=?, doc_name=?, status=?,
               reviewed_by=?, reviewed_at=?, scanned_at=?, batch_date=?,
               raw_image_path=?
               WHERE id=?""",
            (property_id, dt_id, doc_name, status,
             reviewed_by, reviewed_at, NOW, "2026-04-02",
             jpg_name, row["id"]),
        )
        return row["id"], "updated"
    else:
        cur = conn.execute(
            """INSERT INTO documents
               (client_id, property_id, document_type_id, source_doc_id,
                doc_name, status, reviewed_by, reviewed_at, scanned_at,
                batch_date, raw_image_path)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (client_id, property_id, dt_id, source_id,
             doc_name, status, reviewed_by, reviewed_at, NOW,
             "2026-04-02", jpg_name),
        )
        return cur.lastrowid, "inserted"


def upsert_field(conn, doc_id, field_key, field_value):
    label = field_key.replace("_", " ").title()
    row = conn.execute(
        "SELECT id FROM document_fields WHERE document_id=? AND field_key=?",
        (doc_id, field_key),
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE document_fields SET field_value=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (field_value, row["id"]),
        )
    else:
        conn.execute(
            """INSERT INTO document_fields
               (document_id, field_key, field_label, field_value, source)
               VALUES (?,?,?,?,'test-setup')""",
            (doc_id, field_key, label, field_value),
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not DB_PATH.exists():
        print(f"ERROR: portal.db not found at {DB_PATH}")
        sys.exit(1)

    print()
    print("  MorphIQ — Set Test Verification States (Direct DB)")
    print(f"  Client : {CLIENT}")
    print(f"  DB     : {DB_PATH}")
    print(f"  Docs   : {len(SCENARIO)}")
    print()

    conn = get_db()

    # ── Ensure client ────────────────────────────────────────────────────────
    client_id = ensure_client(conn)
    conn.commit()
    print(f"  Client id = {client_id}")
    print()

    # ── Process each document ─────────────────────────────────────────────────
    inserted = updated = fields_written = 0
    current_addr = None

    for (source_id, address, dt_key, status, expiry, doc_name, jpg_name) in SCENARIO:

        if address != current_addr:
            print(f"  {address}")
            current_addr = address

        property_id = ensure_property(conn, client_id, address)
        dt_id       = ensure_document_type(conn, dt_key)
        doc_id, action = upsert_document(
            conn, client_id, property_id, dt_id,
            source_id, doc_name, status, jpg_name,
        )

        if action == "inserted":
            inserted += 1
        else:
            updated += 1

        # Write property_address field (always)
        upsert_field(conn, doc_id, "property_address", address)
        fields_written += 1

        # Write expiry field if applicable
        expiry_key = EXPIRY_KEY.get(dt_key)
        if expiry_key and expiry:
            upsert_field(conn, doc_id, expiry_key, expiry)
            fields_written += 1
            expiry_display = f"  {expiry_key}={expiry}"
        else:
            expiry_display = ""

        status_icon = "+" if action == "inserted" else "~"
        label = DT_LABEL.get(dt_key, dt_key)
        print(f"    [{status_icon}] [{status:<14}]  {label:<35}{expiry_display}")

    conn.commit()
    conn.close()

    print()
    print(f"  Inserted: {inserted}  Updated: {updated}  Fields written: {fields_written}")
    print()

    # ── Verification report ───────────────────────────────────────────────────
    print("=" * 70)
    print("  VERIFICATION REPORT")
    print("=" * 70)

    conn = get_db()
    rows = conn.execute(
        """SELECT
               p.address,
               dt.key        AS doc_type,
               d.status,
               GROUP_CONCAT(df.field_key || '=' || df.field_value, ' | ') AS expiry_fields
           FROM documents d
           JOIN properties p      ON p.id = d.property_id
           JOIN document_types dt ON dt.id = d.document_type_id
           LEFT JOIN document_fields df
               ON df.document_id = d.id
               AND df.field_key IN ('expiry_date','next_inspection_date','valid_until')
           WHERE d.client_id = ?
           GROUP BY d.id
           ORDER BY p.address, dt.key""",
        (client_id,),
    ).fetchall()
    conn.close()

    current_addr = None
    ok = warn = 0
    for r in rows:
        if r["address"] != current_addr:
            print(f"\n  {r['address']}")
            current_addr = r["address"]
        ef = r["expiry_fields"] or "(no expiry)"
        flag = ""
        if r["doc_type"] == "unknown":
            flag = "  << BAD TYPE"
            warn += 1
        else:
            ok += 1
        print(f"    [{r['status']:<14}]  {r['doc_type']:<38}  {ef}{flag}")

    print(f"\n  Total: {len(rows)} documents  ({ok} OK, {warn} warnings)")
    print("=" * 70)
    print()

    if warn:
        print("  WARNING: some documents have doc_type=unknown — check above.")
    else:
        print("  All documents look correct.")
        print("  Reload http://127.0.0.1:5000 and select 'Harlow & Essex Lettings'.")
    print()


if __name__ == "__main__":
    main()
