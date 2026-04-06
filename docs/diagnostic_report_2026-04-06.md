# Morph IQ — Full Diagnostic Report
**Audit date:** 2026-04-06
**Branch:** main | No uncommitted changes | Python 3.14.3

---

## 1. ENVIRONMENT

| Item | Status |
|---|---|
| Project path | `Desktop\MorphIQ\Product` |
| Python version | 3.14.3 |
| `.env` file | PRESENT |
| `portal.db` | PRESENT (project root) |
| `compliance_engine.py` | PRESENT (`portal_new/`) |
| `sync_to_portal.py` | PRESENT (project root) |
| `server.py` | PRESENT (project root) |
| `ai_prefill.py` | PRESENT (project root) |
| `auto_ocr_watch.py` | PRESENT (project root) |

---

## 2. DATABASE

**Tables (13 total):**

| Table | Rows | Notes |
|---|---|---|
| `clients` | 17 | Includes junk test entries |
| `properties` | 218 | |
| `documents` | 460 | |
| `document_fields` | 1,614 | |
| `document_types` | 8 | |
| `users` | 2 | |
| `activity_log` | 150 | |
| `compliance_actions` | 24 | |
| `packs` | 1 | |
| `compliance_records` | 0 | Superseded by compliance_actions |
| `tenants` | 0 | Schema exists, never populated |
| `pack_documents` | 0 | |
| `sqlite_sequence` | 8 | Internal |

**Users table:**
```
id=1  filip@morphiq.co.uk  role=admin   client_id=NULL  active=1
id=2  demo@agency.co.uk    role=manager client_id=1     active=1
```

**Clients (17 total):** Northgate Properties, Oakwood Lettings, Riverside Property Management, Ligant Agency, Harlow & Essex Lettings are real. Remainder are junk test entries: CLient 5, DDDD, aaa, sdfahjfkloashj fa, Client1, Test Client, Testing, PROPER TESTING, NUEW PADE, MUAAAD, PDDAA, CLIEEEEEEEEENT.

**Harlow & Essex Lettings:** 38 documents, 7 properties.

---

## 3. AUTHENTICATION

**STATUS: AUTH IS FULLY IMPLEMENTED**

- `flask_login` imported, `LoginManager` configured, `login_view = "login"` set
- `User(UserMixin)` class defined with `id, email, full_name, role, client_id, is_active`
- `@login_required` on every non-login portal route
- `/login` GET + POST, `/logout` — all present and working
- `get_current_client()` at line 179 — tenant isolation helper
- Role-based isolation: `manager` role hard-locked to their `client_id`; `admin` can switch via `?client=` param

**SECURITY GAP:**
- `/pdf/<path:pdf_path>` (line 1215) — NO `@login_required`
- `/pdf-by-id/<source_doc_id>` (line 1228) — NO `@login_required`
- Any unauthenticated user who knows a document path or source_doc_id can fetch PDFs directly.

---

## 4. PORTAL ROUTES

| Route | Method | Login Required | Client Filter | Assessment |
|---|---|---|---|---|
| `/login` | GET | No | No | Complete |
| `/login` | POST | No | No | Complete |
| `/logout` | GET | No | No | Complete |
| `/` | GET | Yes | Yes | Redirects to overview |
| `/overview` | GET | Yes | Yes | Complete |
| `/properties` | GET | Yes | Yes | Complete |
| `/documents` | GET | Yes | Yes | Complete |
| `/packs` | GET | Yes | Yes | Complete |
| `/reports` | GET | Yes | Yes | Complete |
| `/dashboard` | GET | Yes | Yes | Stub — redirects to overview |
| `/archive` | GET | Yes | Yes | Stub — redirects to properties |
| `/compliance` | GET | Yes | Yes | Complete |
| `/property/<id>` | GET | Yes | Yes | Complete |
| `/document/by-id/<id>` | GET | Yes | Yes | Complete |
| `/document/<source_doc_id>` | GET | Yes | Yes | Complete |
| `/settings` | GET | Yes | Yes | Complete |
| `/activity` | GET | Yes | Yes | Complete |
| `/ask-ai` | GET | Yes | Yes | Complete |
| `/ai-chat` | GET | Yes | Yes | Complete |
| `/pdf/<path>` | GET | **NO** | **NO** | **SECURITY GAP** |
| `/pdf-by-id/<id>` | GET | **NO** | **NO** | **SECURITY GAP** |
| `/api/properties` | GET | Yes | Yes | Complete |
| `/api/clients` | GET | Yes | Admin only | Complete |
| `/api/settings/notifications` | POST | Yes | Yes | Complete |
| `/api/settings/users` | GET | Yes | Yes | Complete |
| `/api/activity` | GET | Yes | Yes | Complete |
| `/api/clients/<id>` | DELETE | Yes | Admin only | Complete |
| `/admin/delete-client/<id>` | POST | Yes | Admin only | Complete |
| `/api/properties/<id>` | GET | Yes | Yes | Complete |

---

## 5. PIPELINE

| Component | Status | Notes |
|---|---|---|
| `auto_ocr_watch.py` | Working | Imports `sync_single_doc` from `sync_to_portal` (double-write fix applied). Called at lines 233 and 577. |
| `ai_prefill.py` | Working | Supports 6 doc types: tenancy_agreement, gas_safety, eicr, epc, deposit_protection, inventory. Model `claude-sonnet-4-20250514` hardcoded as default but passed as parameter. |
| `sync_to_portal.py` | Working | Walks `Clients/` dir, upserts documents + fields into `portal.db`. Exposes `sync_single_doc` and `sync_portal_for_clients`. |
| `server.py` | Working | Port 8765, localhost only. Imports sync functions from `sync_to_portal`. |
| `compliance_engine.py` | Working | Tracks: gas-safety-certificate, eicr, epc, deposit-protection. Queries `documents`/`document_fields` directly — `compliance_records` table (0 rows) is unused. |

---

## 6. TEMPLATES

| Template | Route | Extends base.html | JS refs | Assessment |
|---|---|---|---|---|
| `login.html` | `/login` | No | None | Complete |
| `base.html` | (layout) | N/A | Multiple | Complete |
| `overview.html` | `/overview` | Yes | Yes | Complete (has 1 TODO comment) |
| `properties.html` | `/properties` | Yes | Many | Complete |
| `property.html` | `/property/<id>` | Yes | Yes | Complete |
| `documents.html` | `/documents` | Yes | Yes | Complete |
| `document_view.html` | `/document/...` | Yes | pdf.js CDN | Complete |
| `compliance.html` | `/compliance` | Yes | Yes | Complete |
| `packs.html` | `/packs` | Yes | Yes | Complete |
| `reports.html` | `/reports` | Yes | Yes | Complete |
| `settings.html` | `/settings` | Yes | Yes | Complete |
| `activity.html` | `/activity` | Yes | Yes | Complete |
| `ask_ai.html` | `/ask-ai` | Yes | Yes | Complete |
| `ai_chat.html` | `/ai-chat` | Yes | Yes | Complete |
| `portal.html` | (legacy) | Yes | Yes | Appears to be a legacy duplicate |

---

## 7. ISSUES FOUND

### Security
- `portal_new/app.py` lines 1215–1261: `/pdf/` and `/pdf-by-id/` routes have no `@login_required` and no client_id filter. PDFs are fully public if URL is known.

### Hardcoded paths
- `scan_station.html:1136` — `const BASE_PATH = "C:\\ScanSystem_v2"` (display-only but stale)
- `portal_new/app.py:56` — comment references `C:\ScanSystem_v2`
- `portal_new/import_fields.py:7` — comment `cd C:\ScanSystem_v2`
- `server.py:51` — comment references `C:\ScanSystem_v2`
- `auto_ocr_watch.py` — `MAGICK = r"C:\Program Files\ImageMagick-7.1.2-Q16\magick.exe"` hardcoded and machine-specific (functional risk on any other machine)

### TODO comments
- `portal_new/templates/overview.html:202` — `<!-- TODO: wire to API -->`

### Debug/console logging
- `portal_new/static/portal.js:3561` — `console.log("Chat request:", url, options)` left in production JS

### Stale/empty data
- `tenants` table: 0 rows — model exists, never written to
- `compliance_records` table: 0 rows — appears superseded by `compliance_actions`
- `pack_documents` table: 0 rows — Packs feature incomplete
- 12 of 17 clients are obvious junk test entries (DDDD, aaa, MUAAAD, etc.)

### No issues found
- No PostgreSQL/psycopg2 references — clean SQLite throughout
- No `print("DEBUG")` statements in Python files

---

## 8. GIT STATE

| Item | Value |
|---|---|
| Branch | `main` |
| Remote | Up to date with `origin/main` |
| Uncommitted changes | None |
| Untracked | `docs/MorphIQ_Final_Master_Plan.rtf` |

**Last 10 commits:**
```
5b354fe  Add product screenshots
854212e  Add screenshots section with pipeline narrative
3eeb9e2  Remove personal data and internal docs before going public
f11a965  Restructure repo, fix compliance strip, client session, and add README
9a081b9  Full project state — March 2026
f4f0807  Connect portal frontend to real database
862f4e4  Fix UTF-8 encoding and .env API key loading
4ebb472  Add AI prefill pipeline and portal backend
98d443e  Add files via upload
4bc3866  Remove client data from repository
```

---

## 9. SUMMARY

The project is in a solid mid-build state. The full scanning pipeline is wired end-to-end (ScanStation → OCR → AI prefill → ReviewStation → sync → portal), authentication is properly implemented with role-based tenant isolation, and the portal has real data (460 documents, 218 properties, 17 clients). The single most critical live issue is that both PDF-serving routes (`/pdf/` and `/pdf-by-id/`) are unauthenticated — any client's documents are publicly accessible if the URL is guessed or leaked. The compliance engine is functional but architecturally inconsistent: `compliance_records` has 0 rows because the engine queries `documents` and `document_fields` directly, making the table dead weight. The database contains significant junk test data (12 of 17 clients) that must be purged before any real agency onboarding or demo. The Packs feature and Tenants model are scaffolded but not functional. Everything else — routes, templates, pipeline components — is structurally complete with no broken imports or missing files detected.

---

*Report generated by Claude Code diagnostic audit — 2026-04-06*
