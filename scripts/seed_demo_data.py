"""Build a self-contained demo of the MorphIQ portal with synthetic data.

Creates a fresh portal.db plus a Clients/ folder of generated certificate PDFs for
one fictional letting agency. Every name, address and certificate number is made up,
and the postcodes use an area code that does not exist in the UK.

Dates are relative to today, so the compliance dashboard always shows a realistic
mix of valid, expiring, expired and missing certificates.

Usage:
    python scripts/seed_demo_data.py                  # writes to ./demo/
    python scripts/seed_demo_data.py --out some/dir
    MORPHIQ_DEMO_PASSWORD=... python scripts/seed_demo_data.py

Then start the portal against it:
    DATABASE_URL=demo/portal.db MORPHIQ_CLIENTS_DIR=demo/Clients python portal_new/app.py
"""
from __future__ import annotations

import argparse
import os
import secrets
import shutil
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from werkzeug.security import generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "portal_new"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import document_config  # noqa: E402
from init_portal_db import init_db  # noqa: E402

AGENCY = "Northbrook Lettings (Demo)"
AGENCY_SLUG = "northbrook-lettings-demo"

PROPERTIES = [
    "14 Willow Close, Northbrook, NB4 2LT",
    "Flat 3, 27 Kingsway Court, Northbrook, NB1 6QD",
    "8 Orchard Rise, Eastmere, NB7 3HP",
    "52 Station Road, Northbrook, NB2 9AW",
    "Flat 11, The Maltings, Eastmere, NB7 1RX",
    "3 Heather Lane, Westfield, NB9 4JE",
    "19 Church Walk, Northbrook, NB3 8NS",
    "Flat 6, 140 High Street, Westfield, NB9 2BY",
    "71 Meadow View, Eastmere, NB6 5TF",
    "2 Brookside Cottages, Little Hatton, NB8 7DL",
]

ENGINEERS = ["R. Patel", "J. Morrison", "S. Okafor", "L. Byrne", "D. Kowalczyk"]
ELECTRICIANS = [("A. Hughes", "Brightline Electrical"), ("M. Chen", "Volt & Co")]
ASSESSORS = ["K. Fraser", "T. Adeyemi"]
TENANTS = ["Jamie Carter", "Priya Nair", "Tom & Ellie Walsh", "Marek Nowicki", "Hannah Brooks",
           "Sam Osei", "Laura Kent", "Daniel Reyes", "Chloe Park", "Ben Taylor"]


def iso(d: date) -> str:
    return d.isoformat()


def certificate_plan(today: date) -> list[dict]:
    """One row per (property, certificate) with dates chosen to give every status."""
    plan: list[dict] = []
    # Offsets (days from today) of each property's gas certificate expiry.
    # None = certificate missing, so the dashboard shows a gap.
    gas_expiry = [210, 18, -12, 300, 41, None, 150, 6, 260, 95]
    eicr_next = [900, 1300, 400, -30, 1600, 700, None, 1100, 45, 1500]
    epc_valid = [2400, 3000, 1200, 60, 2800, 3300, 2000, None, 1700, 900]
    epc_ratings = ["C", "D", "C", "E", "B", "D", "C", "D", "C", "E"]
    for i, address in enumerate(PROPERTIES):
        if gas_expiry[i] is not None:
            expiry = today + timedelta(days=gas_expiry[i])
            plan.append({
                "property": i, "type": "Gas Safety Certificate",
                "fields": {
                    "property_address": address,
                    "engineer_name": ENGINEERS[i % len(ENGINEERS)],
                    "gas_safe_reg": f"9{i:02d}{(i * 37) % 1000:03d}",
                    "inspection_date": iso(expiry - timedelta(days=365)),
                    "expiry_date": iso(expiry),
                    "appliances_tested": "Boiler, hob" if i % 2 else "Combi boiler",
                    "result": "Pass",
                },
            })
        if eicr_next[i] is not None:
            nxt = today + timedelta(days=eicr_next[i])
            name, company = ELECTRICIANS[i % len(ELECTRICIANS)]
            plan.append({
                "property": i, "type": "EICR",
                "fields": {
                    "property_address": address,
                    "electrician_name": name,
                    "company_name": company,
                    "registration_number": f"NIC-{4100 + i * 13}",
                    "inspection_date": iso(nxt - timedelta(days=5 * 365)),
                    "next_inspection_date": iso(nxt),
                    "overall_result": "Satisfactory" if i != 3 else "Unsatisfactory",
                    "result": "Satisfactory" if i != 3 else "Unsatisfactory",
                },
            })
        if epc_valid[i] is not None:
            valid = today + timedelta(days=epc_valid[i])
            plan.append({
                "property": i, "type": "EPC",
                "fields": {
                    "property_address": address,
                    "epc_rating": epc_ratings[i],
                    "current_rating": epc_ratings[i],
                    "assessor_name": ASSESSORS[i % len(ASSESSORS)],
                    "assessment_date": iso(valid - timedelta(days=10 * 365)),
                    "expiry_date": iso(valid),
                    "valid_until": iso(valid),
                },
            })
        start = today - timedelta(days=60 + i * 47)
        if i not in (2, 8):  # two tenancies are missing their deposit certificate
            plan.append({
                "property": i, "type": "Deposit Protection Certificate",
                "fields": {
                    "property_address": address,
                    "tenant_full_name": TENANTS[i],
                    "deposit_amount": f"{1096 + i * 98}",
                    "scheme_name": "Demo Deposit Scheme",
                    "certificate_number": f"DPS-{70210 + i * 311}",
                    "protection_date": iso(start + timedelta(days=12)),
                    "expiry_date": iso(start + timedelta(days=365 + 90)),
                    "valid_until": iso(start + timedelta(days=365 + 90)),
                },
            })
        plan.append({
            "property": i, "type": "Tenancy Agreement",
            "fields": {
                "property_address": address,
                "tenant_full_name": TENANTS[i],
                "landlord_name": "Northbrook Property Holdings (Demo)",
                "start_date": iso(start),
                "end_date": iso(start + timedelta(days=365)),
                "monthly_rent_amount": f"{950 + i * 85}",
                "deposit_amount": f"{1096 + i * 98}",
                "agreement_date": iso(start - timedelta(days=14)),
            },
        })
    return plan


def write_pdf(path: Path, title: str, fields: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    c.setFillColorRGB(0.11, 0.2, 0.35)
    c.rect(0, height - 32 * mm, width, 32 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(20 * mm, height - 20 * mm, title.upper())
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, height - 27 * mm, "SYNTHETIC DEMO DOCUMENT - NOT A REAL CERTIFICATE")
    c.setFillColorRGB(0.1, 0.1, 0.1)
    y = height - 48 * mm
    for key, value in fields.items():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20 * mm, y, key.replace("_", " ").title())
        c.setFont("Helvetica", 11)
        c.drawString(80 * mm, y, str(value))
        y -= 9 * mm
    c.showPage()
    c.save()


def seed(out_dir: Path, password: str) -> dict:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    clients_dir = out_dir / "Clients"
    db_path = init_db(out_dir / "portal.db")
    document_config.ensure_document_config(str(db_path))

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    today = date.today()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cur = conn.execute(
            "INSERT INTO clients (name, slug, contact_email, is_active) VALUES (?, ?, ?, 1)",
            (AGENCY, AGENCY_SLUG, "office@northbrook-lettings.example"),
        )
        client_id = cur.lastrowid
        pw_hash = generate_password_hash(password)
        conn.executemany(
            "INSERT INTO users (email, password_hash, full_name, role, client_id, is_active, created_at)"
            " VALUES (?, ?, ?, ?, ?, 1, ?)",
            [
                ("admin@morphiq-demo.test", pw_hash, "Demo Admin", "admin", None, now),
                ("manager@morphiq-demo.test", pw_hash, "Alex Morgan", "manager", client_id, now),
            ],
        )
        property_ids = []
        for address in PROPERTIES:
            postcode = address.rsplit(",", 1)[-1].strip()
            cur = conn.execute(
                "INSERT INTO properties (client_id, address, postcode) VALUES (?, ?, ?)",
                (client_id, address, postcode),
            )
            property_ids.append(cur.lastrowid)

        type_ids = {row["label"]: row["id"] for row in conn.execute("SELECT id, label FROM document_types")}
        batch = today - timedelta(days=3)
        for n, item in enumerate(certificate_plan(today), start=1):
            doc_id = f"DOC-{n:05d}"
            address = PROPERTIES[item["property"]]
            doc_name = f"{address.split(',')[0]} - {item['type']}"
            pdf_path = clients_dir / AGENCY / "Batches" / iso(batch) / doc_id / f"{doc_id}.pdf"
            write_pdf(pdf_path, item["type"], item["fields"])
            reviewed = datetime.combine(batch, datetime.min.time()) + timedelta(hours=9, minutes=n * 4)
            cur = conn.execute(
                """INSERT INTO documents
                   (client_id, property_id, document_type_id, source_doc_id, doc_name, status,
                    pdf_path, quality_score, reviewed_by, reviewed_at, scanned_at, batch_date)
                   VALUES (?, ?, ?, ?, ?, 'verified', ?, '0.97', 'Demo Reviewer', ?, ?, ?)""",
                (
                    client_id, property_ids[item["property"]], type_ids.get(item["type"]), doc_id,
                    doc_name, str(pdf_path.resolve()),
                    reviewed.strftime("%Y-%m-%d %H:%M:%S"),
                    (reviewed - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S"),
                    iso(batch),
                ),
            )
            document_id = cur.lastrowid
            conn.executemany(
                "INSERT INTO document_fields (document_id, field_key, field_label, field_value, source)"
                " VALUES (?, ?, ?, ?, 'demo_seed')",
                [(document_id, k, k.replace("_", " ").title(), v) for k, v in item["fields"].items()],
            )
        conn.commit()
        documents = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    finally:
        conn.close()
    return {"db": db_path, "clients": clients_dir, "documents": documents, "properties": len(PROPERTIES)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(PROJECT_ROOT / "demo"), help="output folder (replaced if it exists)")
    args = parser.parse_args()
    password = os.environ.get("MORPHIQ_DEMO_PASSWORD") or secrets.token_urlsafe(12)
    result = seed(Path(args.out), password)
    print(f"Demo ready: {result['properties']} properties, {result['documents']} documents")
    print(f"  DATABASE_URL={result['db']}")
    print(f"  MORPHIQ_CLIENTS_DIR={result['clients']}")
    print("  Log in as admin@morphiq-demo.test or manager@morphiq-demo.test")
    if not os.environ.get("MORPHIQ_DEMO_PASSWORD"):
        print(f"  Password (generated for this demo only): {password}")


if __name__ == "__main__":
    main()
