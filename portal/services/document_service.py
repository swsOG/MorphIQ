"""Portal query service for document, property, tenant, and compliance APIs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from .db import get_cursor, get_database_url


@dataclass
class SearchFilters:
    property_id: int | None = None
    tenant: str | None = None
    address: str | None = None
    document_type: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    q: str | None = None
    limit: int = 100
    offset: int = 0


class PortalQueryService:
    @staticmethod
    def _using_sqlite() -> bool:
        """Detect whether the active DATABASE_URL points at SQLite."""
        try:
            dsn = get_database_url()
        except RuntimeError:
            return False
        return dsn.startswith("sqlite")

    def _adapt_query(self, query: str) -> str:
        """Swap PostgreSQL-style %s placeholders for SQLite-style ? where needed."""
        if self._using_sqlite():
            return query.replace("%s", "?")
        return query

    def _execute(self, cur, query: str, params: tuple[Any, ...] | None = None) -> None:
        """Helper to run a query with placeholders adapted for the current backend."""
        sql = self._adapt_query(query)
        cur.execute(sql, params)

    def search_documents(self, filters: SearchFilters) -> list[dict[str, Any]]:
        where = ["1=1"]
        params: list[Any] = []

        if filters.property_id is not None:
            where.append("d.property_id = %s")
            params.append(filters.property_id)

        if filters.tenant:
            where.append(
                "EXISTS (SELECT 1 FROM tenants t WHERE t.property_id = d.property_id AND t.client_id = d.client_id AND t.full_name ILIKE %s)"
            )
            params.append(f"%{filters.tenant}%")

        if filters.address:
            where.append("p.address ILIKE %s")
            params.append(f"%{filters.address}%")

        if filters.document_type:
            where.append("dt.label ILIKE %s")
            params.append(f"%{filters.document_type}%")

        if filters.date_from:
            where.append("COALESCE(d.scanned_at::date, d.batch_date) >= %s")
            params.append(filters.date_from)

        if filters.date_to:
            where.append("COALESCE(d.scanned_at::date, d.batch_date) <= %s")
            params.append(filters.date_to)

        if filters.q:
            where.append("(d.doc_name ILIKE %s OR d.source_doc_id ILIKE %s OR COALESCE(d.full_text, '') ILIKE %s)")
            term = f"%{filters.q}%"
            params.extend([term, term, term])

        query = f"""
        SELECT
        id,
        source_doc_id,
        doc_name,
        status,
        scanned_at,
        pdf_path
        FROM documents
        WHERE {' AND '.join(where)}
        ORDER BY COALESCE(scanned_at, imported_at, batch_date) DESC, id DESC
        LIMIT %s OFFSET %s
        """
        params.extend([filters.limit, filters.offset])

        with get_cursor() as cur:
            self._execute(cur, query, tuple(params))
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def get_document(self, document_id: int) -> dict[str, Any] | None:
        with get_cursor() as cur:
            self._execute(
                """
                SELECT
                    d.id,
                    d.source_doc_id,
                    d.doc_name,
                    d.status,
                    d.pdf_path,
                    d.raw_image_path,
                    d.full_text,
                    d.quality_score,
                    d.reviewed_by,
                    d.reviewed_at,
                    d.scanned_at,
                    d.exported_at,
                    d.imported_at,
                    d.batch_date,
                    p.id AS property_id,
                    p.address AS property_address,
                    dt.id AS document_type_id,
                    dt.label AS document_type,
                    c.id AS client_id,
                    c.name AS client_name
                FROM documents d
                LEFT JOIN properties p ON p.id = d.property_id
                LEFT JOIN document_types dt ON dt.id = d.document_type_id
                JOIN clients c ON c.id = d.client_id
                WHERE d.id = %s
                """,
                (document_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            document = dict(row)

            self._execute(
                """
                SELECT field_key, field_label, field_value, source, updated_at
                FROM document_fields
                WHERE document_id = %s
                ORDER BY field_key
                """,
                (document_id,),
            )
            document["fields"] = [dict(r) for r in cur.fetchall()]
            return document

    def get_document_metadata(self, document_id: int) -> dict[str, Any] | None:
        with get_cursor() as cur:
            self._execute(
                """
                SELECT
                    d.id,
                    d.source_doc_id,
                    d.doc_name,
                    d.status,
                    d.batch_date,
                    d.scanned_at,
                    d.reviewed_at,
                    d.exported_at,
                    d.imported_at,
                    d.quality_score,
                    d.reviewed_by,
                    p.id AS property_id,
                    p.address AS property_address,
                    dt.id AS document_type_id,
                    dt.label AS document_type,
                    c.id AS client_id,
                    c.name AS client_name
                FROM documents d
                LEFT JOIN properties p ON p.id = d.property_id
                LEFT JOIN document_types dt ON dt.id = d.document_type_id
                JOIN clients c ON c.id = d.client_id
                WHERE d.id = %s
                """,
                (document_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_property(self, property_id: int) -> dict[str, Any] | None:
        with get_cursor() as cur:
            self._execute(
                """
                SELECT p.id, p.address, p.postcode, p.notes, p.created_at, c.id AS client_id, c.name AS client_name
                FROM properties p
                JOIN clients c ON c.id = p.client_id
                WHERE p.id = %s
                """,
                (property_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            property_data = dict(row)

            self._execute(
                """
                SELECT d.id, d.source_doc_id, d.doc_name, d.status, dt.label AS document_type, d.batch_date, d.pdf_path
                FROM documents d
                LEFT JOIN document_types dt ON dt.id = d.document_type_id
                WHERE d.property_id = %s
                ORDER BY COALESCE(d.scanned_at, d.imported_at) DESC, d.id DESC
                """,
                (property_id,),
            )
            property_data["documents"] = [dict(r) for r in cur.fetchall()]

            self._execute(
                """
                SELECT id, full_name, email, phone, tenancy_start, tenancy_end, created_at
                FROM tenants
                WHERE property_id = %s
                ORDER BY full_name
                """,
                (property_id,),
            )
            property_data["tenants"] = [dict(r) for r in cur.fetchall()]
            return property_data

    def get_tenant(self, tenant_id: int) -> dict[str, Any] | None:
        with get_cursor() as cur:
            self._execute(
                """
                SELECT
                    t.id,
                    t.full_name,
                    t.email,
                    t.phone,
                    t.tenancy_start,
                    t.tenancy_end,
                    t.created_at,
                    t.property_id,
                    p.address AS property_address,
                    t.client_id,
                    c.name AS client_name
                FROM tenants t
                LEFT JOIN properties p ON p.id = t.property_id
                JOIN clients c ON c.id = t.client_id
                WHERE t.id = %s
                """,
                (tenant_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            tenant = dict(row)

            if tenant["property_id"]:
                self._execute(
                    """
                    SELECT d.id, d.source_doc_id, d.doc_name, d.status, dt.label AS document_type, d.batch_date, d.pdf_path
                    FROM documents d
                    LEFT JOIN document_types dt ON dt.id = d.document_type_id
                    WHERE d.property_id = %s
                    ORDER BY COALESCE(d.scanned_at, d.imported_at) DESC, d.id DESC
                    """,
                    (tenant["property_id"],),
                )
                tenant["documents"] = [dict(r) for r in cur.fetchall()]
            else:
                tenant["documents"] = []

            return tenant

    def compliance_status(self, *, property_id: int | None = None, tenant: str | None = None) -> dict[str, Any]:
        where = ["1=1"]
        params: list[Any] = []

        if property_id is not None:
            where.append("cr.property_id = %s")
            params.append(property_id)

        if tenant:
            where.append(
                "EXISTS (SELECT 1 FROM tenants t WHERE t.property_id = cr.property_id AND t.client_id = cr.client_id AND t.full_name ILIKE %s)"
            )
            params.append(f"%{tenant}%")

        with get_cursor() as cur:
            self._execute(
                f"""
                SELECT cr.status, COUNT(*) AS count
                FROM compliance_records cr
                WHERE {' AND '.join(where)}
                GROUP BY cr.status
                """,
                tuple(params),
            )
            counts = {row["status"]: int(row["count"]) for row in cur.fetchall()}

            self._execute(
                f"""
                SELECT
                    cr.id,
                    cr.record_type,
                    cr.expiry_date,
                    cr.status,
                    cr.details,
                    d.id AS document_id,
                    d.source_doc_id,
                    d.doc_name,
                    p.id AS property_id,
                    p.address AS property_address
                FROM compliance_records cr
                JOIN documents d ON d.id = cr.document_id
                LEFT JOIN properties p ON p.id = cr.property_id
                WHERE {' AND '.join(where)}
                ORDER BY cr.expiry_date ASC
                LIMIT 200
                """,
                tuple(params),
            )
            records = [dict(r) for r in cur.fetchall()]

        return {
            "summary": {
                "expired": counts.get("expired", 0),
                "expiring_soon": counts.get("expiring_soon", 0),
                "valid": counts.get("valid", 0),
                "upcoming": counts.get("upcoming", 0),
            },
            "records": records,
        }


def parse_date_param(raw: str | None) -> date | None:
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Invalid date format: {raw}")
