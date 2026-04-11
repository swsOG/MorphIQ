# MORPH IQ — CODEBASE AUDIT

> **Generated:** 2026-04-09
> **Scope:** portal_new/, ai_prefill.py, sync_to_portal.py, auto_ocr_watch.py, portal.db
> **Purpose:** Exhaustive documentation of what exists today. No suggestions — facts only.

---

## 1. DATABASE SCHEMA (ACTUAL)

**File:** `portal.db` (SQLite, project root)

### Tables

#### `clients`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| name | TEXT NOT NULL | |
| slug | TEXT UNIQUE NOT NULL | |
| contact_email | TEXT | |
| contact_phone | TEXT | |
| is_active | INTEGER NOT NULL DEFAULT 1 | |
| created_at | TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP | |
| deleted_at | TEXT | Added by soft_delete migration |

#### `properties`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| client_id | INTEGER NOT NULL | FK → clients(id) ON DELETE CASCADE |
| address | TEXT NOT NULL | |
| postcode | TEXT | |
| notes | TEXT | |
| created_at | TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP | |
| deleted_at | TEXT | Added by soft_delete migration |
| | | UNIQUE (client_id, address) |

**Index:** `idx_properties_client_id` on `client_id`

#### `documents`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| client_id | INTEGER NOT NULL | FK → clients(id) ON DELETE CASCADE |
| property_id | INTEGER | FK → properties(id) ON DELETE SET NULL |
| document_type_id | INTEGER | FK → document_types(id) ON DELETE SET NULL |
| source_doc_id | TEXT NOT NULL | e.g. "DOC-00001" |
| doc_name | TEXT | |
| status | TEXT NOT NULL DEFAULT 'active' | Values: new, ai_prefilled, verified, needs_review, failed |
| pdf_path | TEXT | Absolute path on disk |
| raw_image_path | TEXT | |
| full_text | TEXT | Never populated by current code |
| quality_score | TEXT | |
| reviewed_by | TEXT | |
| reviewed_at | TEXT | |
| scanned_at | TEXT | |
| exported_at | TEXT | |
| imported_at | TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP | |
| batch_date | TEXT | |
| deleted_at | TEXT | Added by soft_delete migration |
| | | UNIQUE (client_id, source_doc_id) |

**Indexes:** `idx_documents_client_id`, `idx_documents_property_id`, `idx_documents_document_type_id`, `idx_documents_source_doc_id`

#### `document_types`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| key | TEXT UNIQUE NOT NULL | e.g. "gas-safety-certificate", "eicr" |
| label | TEXT UNIQUE NOT NULL | e.g. "Gas Safety Certificate", "EICR" |
| description | TEXT | |
| has_expiry | INTEGER NOT NULL DEFAULT 0 | Never used in app code |
| expiry_field_key | TEXT | Never used in app code |
| is_active | INTEGER NOT NULL DEFAULT 1 | |
| created_at | TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP | |

#### `document_fields`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| document_id | INTEGER NOT NULL | FK → documents(id) ON DELETE CASCADE |
| field_key | TEXT NOT NULL | e.g. "expiry_date", "property_address" |
| field_label | TEXT | |
| field_value | TEXT | |
| source | TEXT NOT NULL DEFAULT 'review_json' | |
| created_at | TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP | |
| updated_at | TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP | |
| deleted_at | TEXT | Added by soft_delete migration |
| | | UNIQUE (document_id, field_key) |

**Indexes:** `idx_document_fields_document_id`, `idx_document_fields_field_key`

#### `tenants`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| client_id | INTEGER NOT NULL | FK → clients(id) ON DELETE CASCADE |
| property_id | INTEGER | FK → properties(id) ON DELETE SET NULL |
| full_name | TEXT NOT NULL | |
| email | TEXT | |
| phone | TEXT | |
| tenancy_start | TEXT | |
| tenancy_end | TEXT | |
| created_at | TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP | |
| deleted_at | TEXT | |
| | | UNIQUE (client_id, property_id, full_name) |

**Status:** 0 rows. Schema exists but never populated by any code. Tenant data is derived at runtime from tenancy-agreement document_fields.

#### `compliance_records`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| client_id | INTEGER NOT NULL | FK → clients(id) |
| property_id | INTEGER | FK → properties(id) |
| document_id | INTEGER NOT NULL | FK → documents(id) |
| record_type | TEXT NOT NULL | |
| expiry_date | TEXT NOT NULL | |
| status | TEXT NOT NULL DEFAULT 'upcoming' | |
| details | TEXT | |
| created_at | TEXT | |
| updated_at | TEXT | |
| deleted_at | TEXT | |
| | | UNIQUE (document_id, record_type) |

**Status:** 0 rows. Dead weight — superseded by compliance_actions + compliance_engine.py runtime queries. Has 3 indexes (`idx_compliance_records_client_id`, `idx_compliance_records_expiry_date`, `idx_compliance_records_status`).

#### `compliance_actions`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| client_id | INTEGER NOT NULL | |
| property_id | INTEGER NOT NULL | |
| comp_type | TEXT NOT NULL | e.g. "gas_safety", "eicr" |
| status | TEXT NOT NULL | "open", "resolved", "snoozed" |
| snoozed_until | TEXT | |
| resolved_at | TEXT | |
| resolved_by | TEXT | |
| notes | TEXT | |
| created_at | TEXT | |
| deleted_at | TEXT | |
| | | UNIQUE(client_id, property_id, comp_type) |

**Status:** 24 rows as of 2026-04-06. Created by inline migration in `ensure_compliance_actions_table()`.

#### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PRIMARY KEY | No AUTOINCREMENT |
| email | TEXT UNIQUE NOT NULL | |
| password_hash | TEXT NOT NULL | Werkzeug generate_password_hash |
| full_name | TEXT NOT NULL | |
| role | TEXT NOT NULL DEFAULT 'manager' | Values: "admin", "manager" |
| client_id | INTEGER | NULL for admins, FK to clients(id) for managers |
| is_active | INTEGER DEFAULT 1 | |
| created_at | TEXT | |
| last_login | TEXT | |
| deleted_at | TEXT | |

**Status:** 3 rows (filip@morphiq.co.uk=admin, demo@agency.co.uk=manager, sydney@morphiq.co.uk=manager).

#### `activity_log`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| client_id | INTEGER | |
| user_id | INTEGER | |
| action | TEXT NOT NULL | e.g. "user_login", "document_uploaded", "compliance_resolved" |
| entity_type | TEXT | |
| entity_id | INTEGER | |
| description | TEXT | |
| metadata | TEXT | JSON string |
| created_at | TEXT DEFAULT (datetime('now')) | |
| deleted_at | TEXT | |

**Status:** Created by inline migration in `ensure_activity_log_table()`.

#### `packs`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| client_id | INTEGER NOT NULL | FK → clients(id) |
| name | TEXT NOT NULL | |
| notes | TEXT DEFAULT '' | |
| created_by | INTEGER | FK → users(id) |
| created_at | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | |
| updated_at | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | |
| deleted_at | TEXT | |

**Status:** 1 row as of 2026-04-06. Created by inline migration in `ensure_packs_tables()`.

#### `pack_documents`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| pack_id | INTEGER NOT NULL | FK → packs(id) ON DELETE CASCADE |
| document_id | INTEGER NOT NULL | FK → documents(id) |
| sort_order | INTEGER DEFAULT 0 | |
| added_at | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | |

**Status:** 0 rows.

#### `sqlite_sequence`
Internal SQLite table for AUTOINCREMENT tracking.

### Tables referenced in code but not in DB schema
None — all tables are created either in the original schema or by inline migrations at startup.

### Tables in DB not referenced in code
- `compliance_records` — has 0 rows, has indexes, is never read or written by current code. Dead weight.
- `tenants` — has 0 rows, never read or written. Tenant data derived from document_fields at runtime.
- `document_types.has_expiry` and `document_types.expiry_field_key` columns exist but are never read by any code. Expiry logic is hardcoded in compliance_engine.py and app.py.

---

## 2. API ENDPOINTS (ACTUAL)

**File:** `portal_new/app.py` (4,966 lines)

### Page Routes (all @login_required except login/logout)

| Method | Path | Template | Status |
|--------|------|----------|--------|
| GET | `/login` | login.html | Functional — public |
| POST | `/login` | login.html | Functional — authenticates against users table |
| GET | `/logout` | redirect → /login | Functional |
| GET | `/` | redirect → /overview | Functional |
| GET | `/overview` | overview.html | Functional — shows client picker (admin, no client) or dashboard |
| GET | `/properties` | properties.html | Functional — split-panel layout |
| GET | `/documents` | documents.html | Functional — search + filter library |
| GET | `/packs` | packs.html | Functional |
| GET | `/reports` | reports.html | Functional |
| GET | `/compliance` | compliance.html | Functional — risk banner + matrix |
| GET | `/settings` | settings.html | Functional — account, team, notifications |
| GET | `/ask-ai` | ask_ai.html | Functional |
| GET | `/property/<int:property_id>` | property.html | Functional |
| GET | `/document/by-id/<int:doc_id>` | document_view.html | Functional |
| GET | `/document/<path:source_doc_id>` | document_view.html | Functional |
| GET | `/pdf/<path:pdf_path>` | send_file PDF | Functional — @login_required + tenant scope |
| GET | `/pdf-by-id/<source_doc_id>` | send_file PDF | Functional — @login_required + tenant scope |
| GET | `/dashboard` | redirect → /overview | Redirect alias |
| GET | `/archive` | redirect → /properties | Redirect alias |
| GET | `/activity` | redirect → /reports | Redirect alias |
| GET | `/ai-chat` | redirect → /ask-ai | Redirect alias |

### Client filtering
- **Manager users:** `get_current_client()` resolves their `client_id` from the users table → always locked to one client.
- **Admin users:** `?client=X` query parameter, persisted in Flask session. Cleared by passing `?client=` (empty).
- All API endpoints that accept `?client=` filter by `c.name = ?` in SQL. No client_id-based filtering — always by client name string match.

### JSON API Routes (all @login_required)

| Method | Path | Client filtered | Functional? | Notes |
|--------|------|----------------|-------------|-------|
| GET | `/api/properties` | Yes (c.name) | Functional | Returns enriched properties with compliance, tenant, doc count |
| GET | `/api/properties/<id>` | Yes (scope check) | Functional | Full property detail with all docs, compliance, tenant snapshot |
| GET | `/api/properties/<id>/report` | Yes | Functional | Generates PDF property pack summary (ReportLab) |
| POST | `/api/properties/<id>/download-pack` | Yes | Functional | ZIP of all property PDFs |
| GET | `/api/documents` | Yes (c.name) | Functional | Search, type/status filter, sort, limit. Batch field fetch |
| GET | `/api/documents/by-id/<id>` | Yes (scope check) | Functional | Single document detail |
| GET | `/api/documents/<source_doc_id>` | Yes (scope check) | Functional | Single document by source_doc_id |
| GET | `/api/documents/by-id/<id>/pdf` | Yes (scope check) | Functional | Streams PDF from disk |
| GET | `/api/documents/by-source/<source_doc_id>/pdf` | Yes (scope check) | Functional | Streams PDF by source_doc_id |
| POST | `/api/documents/upload` | Yes | Functional | Multipart upload → Clients/<name>/raw/ + .meta.json |
| GET | `/api/packs` | Yes (client_id) | Functional | List packs with document count |
| POST | `/api/packs` | Yes | Functional | Create pack |
| GET | `/api/packs/<id>` | Yes (scope check) | Functional | Pack detail with documents |
| PUT | `/api/packs/<id>` | Yes | Functional | Update pack name/notes |
| DELETE | `/api/packs/<id>` | Yes | Functional | Soft-delete pack |
| POST | `/api/packs/<id>/documents` | Yes | Functional | Add document to pack |
| DELETE | `/api/packs/<id>/documents/<doc_id>` | Yes | Functional | Remove document from pack |
| PUT | `/api/packs/<id>/reorder` | Yes | Functional | Reorder pack documents |
| GET | `/api/packs/<id>/export/zip` | Yes | Functional | Download pack as ZIP |
| GET | `/api/packs/<id>/export/pdf` | Yes | Functional | Download pack as merged PDF |
| GET | `/api/compliance` | Yes (c.name) | Functional | Full compliance snapshot: stats, actions, health_by_type, resolved |
| GET | `/api/compliance/report` | Yes | Functional | PDF compliance report |
| POST | `/api/compliance/actions/resolve` | Yes | Functional | Resolve a compliance action |
| POST | `/api/compliance/actions/snooze` | Yes | Functional | Snooze a compliance action |
| DELETE | `/api/compliance/actions/resolved` | No (admin) | Functional | Clear all resolved actions |
| GET | `/api/dashboard-stats` | Yes (c.name) | Functional | Score, coverage bars, recent activity |
| GET | `/api/stats` | No (global) | Functional | Simple global counts |
| GET | `/api/activity` | Yes (client_id) | Functional | Paginated activity log with user join |
| GET | `/api/clients` | No | Functional | List active clients for picker |
| DELETE | `/api/clients/<id>` | No | Functional | Hard-delete client cascade |
| POST | `/admin/clients` | No (admin) | Functional | Create new client |
| POST | `/admin/users` | No (admin) | Functional | Create user with hashed password |
| POST | `/admin/delete-client/<id>` | No (admin) | Functional | Soft-delete client (30-day retention) |
| GET | `/api/settings/users` | No (global) | Functional | List all users — NOT scoped per client |
| POST | `/api/settings/notifications` | — | Placeholder | Returns `{"success": true}`, nothing persisted |
| POST | `/api/settings/password` | Own user | Functional | Change own password |
| POST | `/api/chat` | Yes | Functional | Claude-backed chat with portfolio context |

---

## 3. FRONTEND PAGES (ACTUAL)

### Template Files

| Template | Route | API Calls (from JS) | Notes |
|----------|-------|---------------------|-------|
| `login.html` | GET/POST `/login` | None | Standalone, no base.html. Form POSTs to `/login` |
| `base.html` | (layout) | None | Sidebar nav partial, header, Add-to-Pack modal. Loads `portal.js` |
| `overview.html` | `/overview` | `GET /api/dashboard-stats`, `GET /api/compliance` | Standalone (does NOT extend base.html). Inline JS builds ring chart, coverage bars, timeline, activity. Has client picker for admin with no client selected |
| `properties.html` | `/properties` | `GET /api/properties`, `GET /api/properties/<id>` | Extends base.html. Loads `properties.js`. Split-panel layout |
| `compliance.html` | `/compliance` | `GET /api/compliance`, `GET /api/properties` | Standalone (does NOT extend base.html). Inline JS builds risk banner + matrix table. Has upload modal with hardcoded doc types |
| `documents.html` | `/documents` | `GET /api/documents` | Extends base.html. Loads `documents.js`. Grid/list toggle, type pills, status pills, sort, search |
| `packs.html` | `/packs` | `GET /api/packs`, pack CRUD endpoints | Extends base.html |
| `ask_ai.html` | `/ask-ai` | `POST /api/chat` | Extends base.html |
| `reports.html` | `/reports` | `GET /api/activity`, `GET /api/compliance/report` | Extends base.html |
| `settings.html` | `/settings` | `GET /api/settings/users`, `GET /api/clients`, admin CRUD | Extends base.html |
| `property.html` | `/property/<id>` | `GET /api/properties/<id>` | Extends base.html |
| `document_view.html` | `/document/by-id/<id>`, `/document/<source_doc_id>` | `GET /api/documents/by-id/<id>` | Extends base.html |
| `portal.html` | — | — | **Not served by any route.** Orphan template |
| `ai_chat.html` | — | — | **Not served by any route.** Orphan template |
| `partials/portal_sidebar_nav.html` | Included by base.html, overview.html, compliance.html | — | Sidebar with 8 nav links |
| `partials/ai_chat_float_icon.html` | Included by overview.html, compliance.html | — | SVG icon for AI chat FAB |

### JS Files
| File | Loaded by | Description |
|------|-----------|-------------|
| `static/portal.js` | base.html, overview.html, compliance.html | Global: search, notifications, Add-to-Pack modal, AI chat sidebar, client picker |
| `static/js/properties.js` | properties.html | Properties page: list rendering, detail fetch, compliance strip, doc tabs/cards |
| `static/js/documents.js` | documents.html | Documents library: search, type/status filtering, grid/list rendering |

### CSS Files
| File | Loaded by |
|------|-----------|
| `static/portal.css` | All pages (base.html or standalone) |
| `static/css/portal.css` | overview.html, compliance.html (additional dark theme styles) |

---

## 4. HARDCODED LETTING-AGENCY REFERENCES

### compliance_engine.py

| Line | Reference |
|------|-----------|
| 26-42 | `COMPLIANCE_RULES` dict: keys `"gas-safety-certificate"`, `"eicr"`, `"epc"`, `"deposit-protection"` with names `"gas_safety"`, `"eicr"`, `"epc"`, `"deposit"` |
| 27-29 | Gas safety: expiry fields `["expiry_date", "next_inspection_date"]` |
| 30-32 | EICR: expiry fields `["next_inspection_date", "expiry_date"]` |
| 33-35 | EPC: expiry fields `["valid_until", "expiry_date"]` |
| 36-38 | Deposit: expiry fields `["expiry_date"]` |
| 208-213 | `OTHER_EXPIRY_FIELD_CANDIDATES` tuple for non-required doc types |
| 305-345 | `build_summary()`: hardcoded keys `gas_expiring`, `gas_expired`, `gas_missing`, `eicr_expiring`, `epc_missing`, `deposit_missing` |

### app.py

| Line | Reference |
|------|-----------|
| 463-471 | `COMPLIANCE_EXPIRY_FIELDS`: keys for gas-safety-certificate, eicr, epc, deposit-protection (with multiple slug variants) |
| 474-491 | `COMPLIANCE_TYPE_META`: maps `gas_safety`, `eicr`, `epc`, `deposit` to slugs and labels |
| 592-601 | `_severity_text()`: hardcoded fine amounts — "£6,000 fine" (gas), "£30,000 fine" (EICR), "3x deposit" (deposit) |
| 641-671 | Action text per type: "arrange gas safety inspection", "arrange electrical inspection", "arrange EPC assessment", "upload deposit protection certificate" |
| 653-659 | EPC-specific rating extraction: `current_rating`, `potential_rating` |
| 1309-1326 | `api_properties()` inline `_CERT_RULES` dict: duplicates compliance_engine.COMPLIANCE_RULES |
| 1955-1999 | Property detail: hardcoded per-slug summary builders (gas-safety-certificate, eicr, epc, tenancy-agreement, deposit-protection) |
| 2069-2082 | PDF report: hardcoded compliance labels "Gas Safety", "EICR", "EPC", "Deposit" |
| 2178-2189 | Property report: hardcoded slug → key_fields_summary mapping |
| 2661-2668 | `ALLOWED_DOCUMENT_TYPES` set: "Gas Safety Certificate", "EICR", "EPC", "Deposit Protection Certificate", "Tenancy Agreement", "Other" |
| 3378-3379 | Compliance snapshot: `TYPES = ["gas_safety", "eicr", "epc", "deposit"]` |

### ai_prefill.py

| Line | Reference |
|------|-----------|
| 84-114 | `build_tenancy_agreement_prompt()`: hardcoded fields (property_address, tenant_full_name, landlord_name, start_date, end_date, monthly_rent_amount, deposit_amount, agreement_date) |
| 117-144 | `build_gas_safety_prompt()`: hardcoded fields (property_address, engineer_name, gas_safe_reg, inspection_date, expiry_date, appliances_tested, result) |
| 147-176 | `build_eicr_prompt()`: hardcoded fields (property_address, electrician_name, company_name, registration_number, inspection_date, next_inspection_date, overall_result, observations) |
| 179-202 | `build_epc_prompt()`: hardcoded fields (property_address, epc_rating, assessor_name, assessment_date, expiry_date) |
| 205-230 | `build_deposit_protection_prompt()`: hardcoded fields (property_address, tenant_full_name, deposit_amount, scheme_name, certificate_number, protection_date) |
| 233-254 | `build_inventory_prompt()`: hardcoded fields (property_address, clerk_name, inspection_date, property_condition_summary) |
| 345-387 | `RECOGNIZED_DOC_TYPES` list and `DOC_TYPE_CONFIG` dict: 6 document types with prompt builders |
| 390-411 | `REQUIRED_FIELDS` dict: per-type required field lists for quality assessment |
| 354-359 | `DETECTION_SYSTEM`/`DETECTION_USER`: AI classification prompt with 6 exact labels |

### sync_to_portal.py

| Line | Reference |
|------|-----------|
| 25-32 | `DOC_TYPE_MAP`: maps 6 doc type labels to slug keys (e.g. "Gas Safety Certificate" → "gas-safety-certificate") |

### auto_ocr_watch.py

| Line | Reference |
|------|-----------|
| 35 | `DEFAULT_DOC_TYPE = "tenancy_agreement"` — hardcoded default template name |
| 33 | `MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16\magick.exe"` — hardcoded Windows path |

### Frontend JS

**properties.js:**
| Line | Reference |
|------|-----------|
| 5 | `CERT_KEYS = ["gas_safety", "eicr", "epc", "deposit"]` |
| 6 | `CERT_SHORT = { gas_safety: "GAS", eicr: "EICR", epc: "EPC", deposit: "DEP" }` |
| 9-14 | `COMP_TO_DOCTYPE`: maps compliance keys to doc type labels ("Gas Safety Certificate", "EICR", "EPC", "Deposit Protection Certificate") |
| 17-22 | `COMP_STRIP_LABELS`: "Gas Safety", "EICR", "EPC", "Deposit" |
| 317-324 | `docTypeLabelClass()`: CSS class selection by slug (gas, eicr, epc, deposit, tenancy) |
| 377-384 | Document tab type ordering: "Gas Safety Certificate", "EICR", "EPC", "Deposit Protection Certificate", "Tenancy Agreement", "Other" |

**documents.js:**
| Line | Reference |
|------|-----------|
| 8-16 | `TYPE_SLUGS` object: gas, eicr, epc, tenancy, deposit, inventory filter keys → slug values |
| 56-63 | `expiryFieldListForSlug()`: hardcoded expiry field candidates per slug |
| 115-124 | `docTypeLabelClass()`: CSS class by slug (gas, eicr, epc, deposit, tenancy, inventory) |

**compliance.html (inline JS):**
| Line | Reference |
|------|-----------|
| 229 | `CERT_KEYS = ["gas_safety", "eicr", "epc", "deposit"]` |
| 230 | `FINE_PER_EXPIRED = 6000` — hardcoded fine amount |
| 95-103 | Table headers: "Gas", "EICR", "EPC", "Deposit", "Overall" |
| 137-143 | Upload modal doc type select: Gas Safety Certificate, EICR, EPC, Deposit Protection Certificate, Tenancy Agreement, Other |

**overview.html (inline JS):**
| Line | Reference |
|------|-----------|
| 397 | `SKIP_KEYS = ["other", "tenancy", "inventory"]` — excluded from coverage bars |

---

## 5. PIPELINE FLOW (ACTUAL)

### Full Document Path

```
1. INGEST
   Image dropped into Clients/<ClientName>/raw/
   Optional: .meta.json sidecar with doc_name, property_address, group_id

2. WATCHER (auto_ocr_watch.py)
   Polls Clients/*/raw/ every 2 seconds
   For each image file (.jpg, .jpeg, .png, .tiff, .tif, .bmp):
     a. wait_until_stable() — polls file size until stable for 1s
     b. preprocess_for_ocr() — ImageMagick: strip, auto-orient, grayscale, 300 DPI, trim, contrast, sharpen
        Output: temp/<client>_<stem>_ocr.png
     c. ocr_to_pdf() — OCRmyPDF: force-ocr, deskew, rotate-pages, tesseract pagesegmode 4, eng
        Output: Clients/<client>/Batches/<date>/DOC-XXXXX/<stem>.pdf
     d. Move raw image into DOC folder
     e. write_review_json() — creates review.json with:
        - doc_id, doc_type="Unknown", doc_type_template="", status="New"
        - files: {pdf, raw_image}, fields: {}, review: {scanned_at}

3. AI PREFILL (ai_prefill.py, called by watcher via subprocess)
   a. Load review.json
   b. If doc_type is empty/unknown/generic → call Claude to classify (DETECTION prompt)
   c. If recognized type → call Claude with type-specific extraction prompt + PDF base64
   d. Parse JSON response → write fields to review.json
   e. compute_quality_assessment() → write completeness_score, missing_fields, needs_attention
   f. Set status="ai_prefilled", save review.json

4. SYNC TO PORTAL (sync_to_portal.py :: sync_single_doc(), called by watcher)
   a. Find review.json in Clients/<client>/Batches/*/<doc_id>/
   b. ensure_client() → get or create client row
   c. ensure_document_type() → get or create document_types row
   d. ensure_property() → get or create property by address
   e. sync_document() → upsert documents row
   f. sync_fields() → upsert document_fields rows

5. PORTAL DISPLAYS (portal_new/app.py)
   GET /api/properties → queries properties + documents + document_fields
   GET /api/compliance → calls compliance_engine.evaluate_compliance()
   compliance_engine reads documents + document_fields directly from portal.db
```

### Multi-page documents
- ScanStation sends `.meta.json` sidecar per page with `group_id` and `page_number`
- ScanStation writes `<group_id>.group_complete` marker when all pages sent
- Watcher `process_complete_groups()` detects marker → `process_group()`:
  - Preprocesses each page separately
  - Merges into multi-page TIFF via ImageMagick
  - OCRs combined TIFF into single PDF
  - Writes review.json with `group_id`, `page_count`, all `raw_images`
  - Runs AI prefill + sync_single_doc same as single-page

### Scripts that reference database tables

| Script | Tables read/written |
|--------|-------------------|
| `sync_to_portal.py` | clients, document_types, properties, documents, document_fields (all CRUD) |
| `compliance_engine.py` | clients, properties, documents, document_types, document_fields (read only) |
| `portal_new/app.py` | All tables (read + write for compliance_actions, activity_log, packs, pack_documents, users) |
| `auto_ocr_watch.py` | None directly — calls sync_to_portal.sync_single_doc() |
| `ai_prefill.py` | None — reads/writes review.json only |

### Hardcoded paths in pipeline
- `auto_ocr_watch.py:33` — `MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16\magick.exe"`
- `auto_ocr_watch.py:35` — `DEFAULT_DOC_TYPE = "tenancy_agreement"`
- `ai_prefill.py:261` — `model: str = "claude-sonnet-4-20250514"` (default Claude model)
- All scripts use `Path(__file__).resolve().parent` for base paths (no hardcoded deploy root)

---

## 6. AUTHENTICATION STATE

### Flask-Login
- **Installed and wired:** Yes. `LoginManager` configured in app.py lines 119-121.
- **login_view:** Set to `"login"` — unauthenticated requests redirect to `/login`.
- **User class:** `User(UserMixin)` at line 123 with `id`, `email`, `full_name`, `role`, `client_id`, `is_active`.
- **user_loader:** `load_user()` at line 148 — queries users table by id, respects `deleted_at IS NULL`.

### Route protection
- **All page routes** (except `/login`, `/logout`) have `@login_required` decorator.
- **All API routes** have `@login_required` decorator.
- **PDF routes** (`/pdf/<path>`, `/pdf-by-id/<source_doc_id>`) have both `@login_required` AND tenant scope checking.

### Session management
- `app.secret_key` set from `PORTAL_SECRET_KEY` env var, defaults to `"morphiq-dev-secret-change-in-prod"`.
- `session["selected_client"]` used to persist admin's client selection across requests.
- No session timeout configuration.
- No CSRF protection.

### Users table data
3 users as of 2026-04-06:

| id | email | role | client_id | is_active |
|----|-------|------|-----------|-----------|
| 1 | filip@morphiq.co.uk | admin | NULL | 1 |
| 2 | demo@agency.co.uk | manager | 1 | 1 |
| 3 | sydney@morphiq.co.uk | manager | 16 (Ligant Agency) | 1 |

### Security issues
- `debug=True` in `app.run()` at line 4966 — Werkzeug debugger with interactive console exposed.
- Default secret key `"morphiq-dev-secret-change-in-prod"` is deterministic.
- No CSRF tokens on any form (login form, settings forms, upload form).
- No rate limiting on login attempts.
- `GET /api/settings/users` returns all users globally regardless of caller's client — a manager at Agency A can see Agency B's users.
- `GET /api/stats` returns global counts without client filtering.

---

## 7. WHAT WORKS VS WHAT'S BROKEN

### What works
- Full login/logout flow with password hashing
- Client picker for admins, hard-lock for managers
- Properties split-panel with compliance badges and document cards
- Compliance matrix with filter chips and risk banner
- Documents library with search, type/status filters, grid/list toggle
- Packs CRUD + ZIP/PDF export
- AI chat with Claude (portfolio-contextualized)
- Activity log with pagination
- PDF serving from disk with tenant scope checking
- Document upload via portal → Clients/<name>/raw/ with .meta.json
- Full OCR pipeline: ImageMagick → OCRmyPDF → review.json → AI prefill → portal sync
- Multi-page document grouping
- Property PDF report generation (ReportLab)
- Compliance report PDF generation
- Compliance action resolve/snooze
- User creation and password change

### Incomplete / stubbed
- `POST /api/settings/notifications` — returns `{"success": true}` without persisting anything (app.py:1549-1553).
- Overview page "My Packs" section is hardcoded placeholder HTML, not wired to API (overview.html:201-213, marked `<!-- TODO: wire to API -->`).
- `portal.html` template exists but no route serves it.
- `ai_chat.html` template exists but no route serves it.
- `compliance_records` table — 0 rows, never used, fully superseded.
- `tenants` table — 0 rows, never populated. Tenant data derived from document_fields.
- `document_types.has_expiry` and `document_types.expiry_field_key` columns exist but are never read.
- `documents.full_text` column exists but is never populated.

### Known bugs / inconsistencies
1. **deposit-protection key mismatch:** `compliance_engine.py` COMPLIANCE_RULES uses key `"deposit-protection"` (line 38). `sync_to_portal.py` DOC_TYPE_MAP maps "Deposit Protection" → `"deposit-protection"`. But app.py `api_properties()` uses `"deposit-protection-certificate"` as the key (line 1325), and many `document_types.key` rows in the DB likely store `"deposit-protection-certificate"`. This means compliance_engine's GROUP BY lookup may miss deposit documents. Properties.js has a client-side workaround.

2. **Duplicate compliance rules:** `app.py:1309-1326` (`api_properties()`) has a full copy of compliance rules (`_CERT_RULES`) inline rather than importing from compliance_engine. These can drift.

3. **Inconsistent status terminology:** `api_properties()` returns status `"expiring"` (line 1490) while compliance_engine returns `"expiring_soon"` (line 84). Properties.js normalizes `"expiring"` and `"expiring_soon"` to the same CSS class, but this is fragile.

4. **`debug=True` in production:** app.py:4966 runs with `debug=True`. Werkzeug interactive debugger is exposed.

5. **Default secret key:** `"morphiq-dev-secret-change-in-prod"` is deterministic and allows session forgery.

6. **Global user listing:** `GET /api/settings/users` returns all users, not scoped by client. A manager can see other agencies' users.

7. **Global stats endpoint:** `GET /api/stats` returns unscoped document counts.

8. **12 junk test clients** remain in DB (per PROJECT_BRAIN.md).

9. **`CHAT REQUEST:` debug print** at app.py:4528-4533 — prints chat payload to stdout on every request.

10. **No CSRF protection** on any form or API endpoint.

11. **overview.html and compliance.html do not extend base.html** — they are standalone templates with duplicated header/sidebar HTML. Changes to the header or sidebar must be made in 3 places (base.html, overview.html, compliance.html).

12. **portal.css loaded twice** in overview.html and compliance.html — both `static/portal.css` and `static/css/portal.css` are linked.

### TODO comments in code
- `overview.html:202` — `<!-- TODO: wire to API -->` (My Packs section)

---

*End of audit.*
