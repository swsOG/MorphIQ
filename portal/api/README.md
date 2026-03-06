# Portal API Endpoints

Base prefix: `/api`

## 1) Document search
`GET /api/documents/search`

Supported query params:
- `property_id`
- `tenant`
- `address`
- `document_type`
- `date_from` (`YYYY-MM-DD`, `DD/MM/YYYY`, or `DD-MM-YYYY`)
- `date_to` (`YYYY-MM-DD`, `DD/MM/YYYY`, or `DD-MM-YYYY`)
- `q` (free text over `doc_name`, `source_doc_id`, `full_text`)
- `limit` (default 100, max 500)
- `offset` (default 0)

Example:
```http
GET /api/documents/search?address=Oak+Road&document_type=Tenancy&date_from=2026-01-01&date_to=2026-12-31
```

Example response:
```json
{
  "count": 1,
  "results": [
    {
      "id": 12,
      "source_doc_id": "DOC-00012",
      "doc_name": "42 Oak Road - Tenancy Agreement 1",
      "status": "Verified",
      "property_id": 4,
      "property_address": "42 Oak Road, Harlow",
      "document_type": "Tenancy Agreement",
      "pdf_path": "C:/ScanSystem_v2/Clients/.../document.pdf"
    }
  ]
}
```

## 2) Document retrieval
`GET /api/documents/<document_id>`

Returns document metadata + `fields[]`.

## 3) Document metadata
`GET /api/documents/<document_id>/metadata`

Returns metadata-only payload without full text + field rows.

## 4) Property view
`GET /api/properties/<property_id>`

Returns property core data with nested `documents[]` and `tenants[]`.

## 5) Tenant view
`GET /api/tenants/<tenant_id>`

Returns tenant core data with nested `documents[]` for tenant's property.

## 6) Compliance status
`GET /api/compliance/status`

Optional filters:
- `property_id`
- `tenant`

Returns:
- `summary` counts (`expired`, `expiring_soon`, `valid`, `upcoming`)
- `records[]` compliance rows
