"""
Compliance evaluation engine for property documents.

This module reads from portal.db and computes, for each property, whether
key compliance documents exist and whether they are valid, expiring soon,
expired, or missing.
"""

import os
import sqlite3
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Set

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL", os.path.join(BASE_DIR, "..", "portal.db"))


# Which document types we care about for compliance and how to interpret them.
#
# The keys here are document_types.key values in the database; the name field
# is how they will appear in the output structure.
#
# expiry_field_candidates is ordered by preference; the first populated field
# on the latest document is treated as the expiry date.
COMPLIANCE_RULES = {
    "gas-safety-certificate": {
        "name": "gas_safety",
        "expiry_field_candidates": ["expiry_date", "next_inspection_date"],
    },
    "eicr": {
        "name": "eicr",
        "expiry_field_candidates": ["next_inspection_date", "expiry_date"],
    },
    "epc": {
        "name": "epc",
        "expiry_field_candidates": ["valid_until", "expiry_date"],
    },
    "deposit-protection-certificate": {
        "name": "deposit",
        "expiry_field_candidates": ["expiry_date"],
    },
}

EXPIRING_SOON_DAYS = 30


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn


def _parse_date(value: str) -> date | None:
    """Best-effort parse of a date string into a date object."""
    if not value:
        return None
    text = value.strip()
    if not text:
        return None

    # Try a few common formats; fall back to None on failure.
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # As a last resort, try letting fromisoformat handle it.
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _status_from_expiry(expiry: date | None, today: date | None = None) -> str:
    """Map an expiry date to one of: valid, expiring_soon, expired."""
    if today is None:
        today = date.today()
    if expiry is None:
        # If we have a document but no usable expiry date, treat it as valid.
        return "valid"
    if expiry < today:
        return "expired"
    if expiry <= today + timedelta(days=EXPIRING_SOON_DAYS):
        return "expiring_soon"
    return "valid"


def evaluate_compliance(client_id: int | None = None) -> List[Dict[str, Any]]:
    """
    Compute compliance status for all properties.

    Returns a list like:
    [
      {
        "property": "14 Elm Street",
        "gas_safety": "valid",
        "eicr": "expired",
        "epc": "missing",
        "deposit": "expiring_soon",
      },
      ...
    ]
    """
    conn = _get_db()
    try:
        # Fetch all properties (including the client name for context).
        if client_id is None:
            props = conn.execute(
                """
                SELECT
                    p.id AS property_id,
                    p.address AS property_address,
                    c.name AS client_name
                FROM properties p
                JOIN clients c ON p.client_id = c.id AND c.deleted_at IS NULL
                WHERE p.deleted_at IS NULL
                """
            ).fetchall()
        else:
            props = conn.execute(
                """
                SELECT
                    p.id AS property_id,
                    p.address AS property_address,
                    c.name AS client_name
                FROM properties p
                JOIN clients c ON p.client_id = c.id AND c.deleted_at IS NULL
                WHERE p.deleted_at IS NULL AND p.client_id = ?
                """,
                (client_id,),
            ).fetchall()

        if not props:
            return []

        # For each property and compliance doc type, find the latest document id.
        property_ids = [row["property_id"] for row in props]
        placeholders = ",".join("?" for _ in property_ids)
        type_keys = list(COMPLIANCE_RULES.keys())
        type_placeholders = ",".join("?" for _ in type_keys)

        latest_docs_sql = f"""
            SELECT
                d.id AS document_id,
                d.property_id,
                dt.key AS doc_type_key,
                MAX(
                    COALESCE(d.batch_date, d.scanned_at, d.reviewed_at, d.imported_at)
                ) AS latest_timestamp
            FROM documents d
            LEFT JOIN document_types dt ON d.document_type_id = dt.id
            WHERE
                d.property_id IN ({placeholders})
                AND dt.key IN ({type_placeholders})
                AND d.deleted_at IS NULL
            GROUP BY d.property_id, dt.key
        """
        latest_rows = conn.execute(
            latest_docs_sql,
            (*property_ids, *type_keys),
        ).fetchall()

        # Build mapping: (property_id, doc_type_key) -> document_id
        latest_map: Dict[tuple[int, str], int] = {}
        for row in latest_rows:
            key = (row["property_id"], row["doc_type_key"])
            latest_map[key] = row["document_id"]

        # Fetch all field rows for the selected documents in one go.
        doc_ids = [row["document_id"] for row in latest_rows]
        fields_by_doc: Dict[int, Dict[str, str]] = {}
        if doc_ids:
            doc_placeholders = ",".join("?" for _ in doc_ids)
            field_rows = conn.execute(
                f"""
                SELECT document_id, field_key, field_value
                FROM document_fields
                WHERE document_id IN ({doc_placeholders})
                  AND deleted_at IS NULL
                """,
                doc_ids,
            ).fetchall()
            for fr in field_rows:
                d_id = fr["document_id"]
                fields_by_doc.setdefault(d_id, {})[fr["field_key"]] = fr["field_value"] or ""

        today = date.today()
        results: List[Dict[str, Any]] = []

        for prop in props:
            prop_id = prop["property_id"]
            entry: Dict[str, Any] = {
                "property": prop["property_address"],
                "client": prop["client_name"],
            }

            for type_key, rule in COMPLIANCE_RULES.items():
                field_name = rule["name"]
                doc_id = latest_map.get((prop_id, type_key))
                if not doc_id:
                    entry[field_name] = "missing"
                    continue

                fields = fields_by_doc.get(doc_id, {})
                expiry_value = None
                for candidate in rule["expiry_field_candidates"]:
                    raw = fields.get(candidate)
                    if raw:
                        expiry_value = _parse_date(raw)
                        if expiry_value:
                            break

                entry[field_name] = _status_from_expiry(expiry_value, today=today)

            results.append(entry)

        return results
    finally:
        conn.close()


def evaluate_compliance_for_client(client_id: int) -> List[Dict[str, Any]]:
    return evaluate_compliance(client_id=client_id)


OTHER_EXPIRY_FIELD_CANDIDATES = (
    "expiry_date",
    "next_inspection_date",
    "valid_until",
    "valid_to",
)


def _status_other_from_fields(fields: Dict[str, str], today: date | None = None) -> str:
    """Classify a non-required document using generic expiry fields (same date rules as required types)."""
    if today is None:
        today = date.today()
    expiry_value = None
    for k in OTHER_EXPIRY_FIELD_CANDIDATES:
        raw = fields.get(k)
        if raw:
            expiry_value = _parse_date(raw)
            if expiry_value:
                break
    return _status_from_expiry(expiry_value, today=today)


def count_properties_with_other_present(conn: sqlite3.Connection, property_ids: List[int]) -> int:
    """
    Number of properties that have at least one document whose type is not in COMPLIANCE_RULES,
    and that document is valid or expiring soon (not expired / not missing).
    """
    if not property_ids:
        return 0
    required_keys = tuple(COMPLIANCE_RULES.keys())
    placeholders = ",".join("?" * len(property_ids))
    req_ph = ",".join("?" * len(required_keys))
    cur = conn.execute(
        f"""
        SELECT DISTINCT dt.key
        FROM documents d
        JOIN document_types dt ON d.document_type_id = dt.id
        WHERE d.property_id IN ({placeholders})
          AND dt.key NOT IN ({req_ph})
          AND d.deleted_at IS NULL
        """,
        (*property_ids, *required_keys),
    )
    other_keys = [r[0] for r in cur.fetchall()]
    if not other_keys:
        return 0
    type_placeholders = ",".join("?" for _ in other_keys)
    prop_placeholders = ",".join("?" for _ in property_ids)
    latest_docs_sql = f"""
        SELECT
            d.id AS document_id,
            d.property_id,
            dt.key AS doc_type_key,
            MAX(
                COALESCE(d.batch_date, d.scanned_at, d.reviewed_at, d.imported_at)
            ) AS latest_timestamp
        FROM documents d
        LEFT JOIN document_types dt ON d.document_type_id = dt.id
        WHERE
            d.property_id IN ({prop_placeholders})
            AND dt.key IN ({type_placeholders})
            AND d.deleted_at IS NULL
        GROUP BY d.property_id, dt.key
    """
    latest_rows = conn.execute(
        latest_docs_sql,
        (*property_ids, *other_keys),
    ).fetchall()
    doc_ids = [row["document_id"] for row in latest_rows]
    fields_by_doc: Dict[int, Dict[str, str]] = {}
    if doc_ids:
        doc_placeholders = ",".join("?" for _ in doc_ids)
        field_rows = conn.execute(
            f"""
            SELECT document_id, field_key, field_value
            FROM document_fields
            WHERE document_id IN ({doc_placeholders})
              AND deleted_at IS NULL
            """,
            doc_ids,
        ).fetchall()
        for fr in field_rows:
            d_id = fr["document_id"]
            fields_by_doc.setdefault(d_id, {})[fr["field_key"]] = fr["field_value"] or ""

    today = date.today()
    good_props: Set[int] = set()
    for row in latest_rows:
        doc_id = row["document_id"]
        pid = row["property_id"]
        fields = fields_by_doc.get(doc_id, {})
        st = _status_other_from_fields(fields, today=today)
        if st in ("valid", "expiring_soon"):
            good_props.add(pid)
    return len(good_props)


def build_summary(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Build high-level alert counts from a list of compliance rows.

    The keys focus on the highest-signal compliance risks for agencies:
      - gas_expiring / gas_expired / gas_missing
      - eicr_expiring
      - epc_missing
      - deposit_missing
    """
    summary: Dict[str, int] = {
        "gas_expiring": 0,
        "gas_expired": 0,
        "gas_missing": 0,
        "eicr_expiring": 0,
        "epc_missing": 0,
        "deposit_missing": 0,
    }

    for row in rows:
        gas = (row.get("gas_safety") or "").strip()
        if gas == "expiring_soon":
            summary["gas_expiring"] += 1
        elif gas == "expired":
            summary["gas_expired"] += 1
        elif gas == "missing":
            summary["gas_missing"] += 1

        eicr = (row.get("eicr") or "").strip()
        if eicr == "expiring_soon":
            summary["eicr_expiring"] += 1

        epc = (row.get("epc") or "").strip()
        if epc == "missing":
            summary["epc_missing"] += 1

        deposit = (row.get("deposit") or "").strip()
        if deposit == "missing":
            summary["deposit_missing"] += 1

    return summary


