"""Portal API routes for search/retrieval/compliance endpoints."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from portal.services import PortalQueryService, SearchFilters, parse_date_param

api_bp = Blueprint("portal_api", __name__, url_prefix="/api")
service = PortalQueryService()


@api_bp.get("/documents/search")
def search_documents():
    """Search documents by property, tenant, address, type, and date filters."""
    try:
        filters = SearchFilters(
            property_id=_to_int(request.args.get("property_id")),
            tenant=request.args.get("tenant"),
            address=request.args.get("address"),
            document_type=request.args.get("document_type"),
            date_from=parse_date_param(request.args.get("date_from")),
            date_to=parse_date_param(request.args.get("date_to")),
            q=request.args.get("q"),
            limit=min(_to_int(request.args.get("limit"), 100) or 100, 500),
            offset=_to_int(request.args.get("offset"), 0) or 0,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    docs = service.search_documents(filters)
    return jsonify({"count": len(docs), "results": docs})


@api_bp.get("/documents/<int:document_id>")
def get_document(document_id: int):
    doc = service.get_document(document_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    return jsonify(doc)


@api_bp.get("/documents/<int:document_id>/metadata")
def get_document_metadata(document_id: int):
    metadata = service.get_document_metadata(document_id)
    if not metadata:
        return jsonify({"error": "Document not found"}), 404
    return jsonify(metadata)


@api_bp.get("/properties/<int:property_id>")
def get_property(property_id: int):
    property_data = service.get_property(property_id)
    if not property_data:
        return jsonify({"error": "Property not found"}), 404
    return jsonify(property_data)


@api_bp.get("/tenants/<int:tenant_id>")
def get_tenant(tenant_id: int):
    tenant = service.get_tenant(tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404
    return jsonify(tenant)


@api_bp.get("/compliance/status")
def get_compliance_status():
    data = service.compliance_status(
        property_id=_to_int(request.args.get("property_id")),
        tenant=request.args.get("tenant"),
    )
    return jsonify(data)


def _to_int(raw: str | None, default: int | None = None) -> int | None:
    if raw is None:
        return default
    raw = raw.strip()
    if not raw:
        return default
    return int(raw)
