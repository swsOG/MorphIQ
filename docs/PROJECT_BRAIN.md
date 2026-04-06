# PROJECT BRAIN — MorphIQ Document Scanning & Compliance Platform

> **Last updated:** 2026-04-06
> **Purpose:** Single source of truth for the current system. Read this before making changes.

---

## BUSINESS

**What:** Document scanning and compliance platform for UK letting agencies. Digitises property certificates, extracts compliance data with AI, and provides a client portal for document access and compliance tracking.

**Value prop:** "Not just scanned — understood." Catches missed certificate expiry dates — protects agencies from fines up to £6,000.

**Target:** Five letting agencies. Each gets isolated login, isolated data, compliance reporting, and document archive.

**Name:** Morph IQ. **Status:** Demo-ready build phase. Legal/commercial handled by Sydney.

---

## CURRENT STATE

### What works today (confirmed)

- **Full pipeline wired end-to-end:** ScanStation → OCR (ImageMagick + OCRmyPDF + Tesseract) → AI prefill (Claude) → ReviewStation → sync_to_portal.py → portal.db → portal UI.
- **Portal authentication:** Flask-Login, login/logout, `@login_required` on all routes. Manager role hard-locked to `client_id`. Admin can switch clients via `?client=` param (persisted in session).
- **PDF routes secured (fixed this session):** `/pdf/<path>` and `/pdf-by-id/<source_doc_id>` now require `@login_required` AND enforce tenant scope via JOIN to clients table. Previously fully public — any URL-knower could download any document.
- **Database reachable from portal (fixed this session):** `DATABASE_URL` now uses `os.path.normpath()` to collapse `..` in path. Flask reloader disabled (`use_reloader=False`) — previously the reloader's child process resolved the path differently and failed silently, causing `sqlite3.OperationalError: unable to open database file` on first DB request (e.g. login POST).
- **Multi-tenant onboarding flow now operational (built this session):**
  - `POST /admin/clients` — create a new agency client (admin only)
  - `POST /admin/users` — create a user with hashed password, assigned to a client (admin only)
  - `POST /api/settings/password` — change own password (any authenticated user)
  - `GET /api/settings/users` — now returns `client_id` and `client_name` (joined)
  - Settings page: Add client form, Add user form (with client dropdown), Change password form, Client column in users table — all wired and live
- **Junk clients still in DB (not yet cleaned):** 12 of 17 clients are test garbage (DDDD, aaa, MUAAAD, etc.). Must be purged before any demo or real onboarding. 5 real clients: Northgate Properties, Oakwood Lettings, Riverside Property Management, Ligant Agency, Harlow & Essex Lettings.
- **ScanStation** (`scan_station.html`): Capture, session queue, rescan flow, Export/Open Portal, camera settings, Live Session Intelligence, multi-page document capture (group_id + .group_complete marker). `BASE_PATH` constant was a stale `C:\ScanSystem_v2` reference — cleaned this session to empty string.
- **ReviewStation** (`review_station.html`): Dashboard, review with PDF/OCR, status workflow, rescan reasons, auto-sync to portal on save, triage/validation (needs_attention, missing_fields, verification gate), merge/split capability.
- **Portal pages (all 8 live):** Overview, Properties (split-panel), Compliance (risk banner + matrix), Documents (search + cards), Packs (builder), Ask AI (chat), Reports, Settings (team + notifications + permissions).
- **Compliance engine:** `compliance_engine.py` tracks gas-safety, EICR, EPC, deposit-protection. Queries documents/document_fields directly. `compliance_records` table (0 rows) is dead weight — superseded.
- **Debug console.log removed (fixed this session):** `portal.js` had `console.log("Chat request:", url, options)` leaking AI chat request payloads to browser DevTools — removed.
- **Stale path references cleaned (this session):** All `C:\ScanSystem_v2` references removed from `scan_station.html`, `portal_new/app.py`, `portal_new/import_fields.py`, `server.py`.

### Not done / product gaps

- Deposit Protection + Inventory **templates** not in `Templates/` (placeholders only).
- **Packs feature:** `pack_documents` table has 0 rows — packs CRUD API built but not fully exercised end-to-end.
- **Tenants table:** 0 rows — schema exists, never populated. Either wire it or drop it.
- `compliance_records` table: 0 rows — superseded by compliance_actions. Dead weight.
- Archive **scoped export** (filter by status/type from UI) still TODO.
- **Multi-page E2E test** not completed — `simulate_multipage.py` created but not run.
- **Full 10-document E2E test** not yet run.
- **Hetzner VPS deployment** — not started.
- **Password reset by email** — deferred until Hetzner (needs SMTP).
- **python-dotenv not installed** — Flask shows yellow warning. Non-blocking. Fix: `pip install python-dotenv`.

---

## DATABASE

**File:** `portal.db` at project root (`Desktop\MorphIQ\Product\portal.db`)

**Tables (13):**
`activity_log`, `clients`, `compliance_actions`, `compliance_records`, `document_fields`, `document_types`, `documents`, `pack_documents`, `packs`, `properties`, `sqlite_sequence`, `tenants`, `users`

**Live counts (queried 2026-04-06):**

| Table | Rows | Notes |
|---|---|---|
| `clients` | 17 | 5 real, 12 junk test entries — must purge |
| `properties` | 218 | |
| `documents` | 460 | |
| `document_fields` | 1,614 | |
| `users` | 3 | |
| `compliance_actions` | 24 | |
| `compliance_records` | 0 | Superseded — dead weight |
| `tenants` | 0 | Schema only — never populated |
| `pack_documents` | 0 | Packs feature incomplete |
| `packs` | 1 | |
| `document_types` | 8 | |

**Clients (17 total — 5 real, 12 junk):**

Real: Northgate Properties (id=11), Oakwood Lettings (id=14), Riverside Property Management (id=15), Ligant Agency (id=16), Harlow & Essex Lettings (id=28)

Junk (must purge): DDDD (17), aaa (18), sdfahjfkloashj fa (19), Client1 (20), Test Client (21), Testing (22), PROPER TESTING (23), NUEW PADE (24), MUAAAD (25), PDDAA (26), CLIEEEEEEEEENT (29)

**Users (3):**

| id | email | role | client_id |
|---|---|---|---|
| 1 | filip@morphiq.co.uk | admin | NULL |
| 2 | demo@agency.co.uk | manager | 1 |
| 3 | sydney@morphiq.co.uk | manager | 16 (Ligant Agency) |

---

## SYSTEM ARCHITECTURE

**Deploy root:** `C:\Users\user\OneDrive - University of East London\Desktop\MorphIQ\Product`

**Core layout:**

```
Product\
├── auto_ocr_watch.py, server.py, export_client.py, sync_to_portal.py, ai_prefill.py
├── scan_station.html, review_station.html, viewer.html
├── Start_System_v2.bat, Stop_System.bat, setup_check.bat
├── bulk_import.py, rerun_prefill.py, generate_test_documents.py
├── set_test_verification_states.py, admin_delete_client.py
├── portal.db                    # SQLite — project root
├── portal_new\                  # Flask portal (port 5000) — CANONICAL
│   ├── app.py
│   ├── compliance_engine.py
│   ├── soft_delete.py
│   ├── import_fields.py
│   ├── templates\               # login, base, overview, properties, etc.
│   └── static\                  # portal.css, portal.js, morph_iq_icon.png
├── portal\                      # OLD portal — abandoned, ignore
├── Clients\<Client>\            # raw\, Batches\, Exports\, Logs\
├── Templates\                   # JSON field templates (5 + general)
└── docs\                        # PROJECT_BRAIN.md, SETUP_GUIDE.md, etc.
```

**Servers:**
- `portal_new/app.py` — Flask, port 5000, `use_reloader=False` (reloader disabled to prevent child process DB path issue)
- `server.py` — ScanStation API, port 8765, localhost only

---

## API ENDPOINTS

### ScanStation API (`server.py`) — port 8765

| Method | Path | Notes |
|--------|------|-------|
| GET | `/health` | Liveness |
| GET | `/clients` | List client folder names |
| GET | `/docs/<client>` | All documents + review payload |
| GET | `/stats/<client>` | Counts by status |
| POST | `/review/<client>/<doc_id>` | Save review → sync_single_doc |
| GET | `/pdf/<client>/<doc_id>` | Serve PDF |
| GET | `/ocr-text/<client>/<doc_id>` | pdfminer text |
| POST | `/export` | Export + sync_portal_for_clients |
| POST | `/merge/<client>` | Merge 2+ docs into one |
| POST | `/split/<client>/<doc_id>` | Split multi-page into individual docs |

### Portal (`portal_new/app.py`) — port 5000

**Page routes (all `@login_required` except login/logout):**

| Path | Method | Notes |
|------|--------|-------|
| `/login` | GET, POST | Public |
| `/logout` | GET | Public |
| `/` | GET | Redirects → /overview |
| `/overview` | GET | Client-scoped |
| `/properties` | GET | Client-scoped |
| `/documents` | GET | Client-scoped |
| `/packs` | GET | Client-scoped |
| `/reports` | GET | Client-scoped |
| `/compliance` | GET | Client-scoped |
| `/settings` | GET | Client-scoped |
| `/activity` | GET | Redirects → /reports |
| `/dashboard` | GET | Redirects → /overview |
| `/archive` | GET | Redirects → /properties |
| `/ai-chat` | GET | Redirects → /ask-ai |
| `/ask-ai` | GET | Client-scoped |
| `/property/<id>` | GET | Client-scoped |
| `/document/by-id/<id>` | GET | Client-scoped |
| `/document/<source_doc_id>` | GET | Client-scoped |
| `/pdf/<path>` | GET | **@login_required + tenant check** (fixed this session) |
| `/pdf-by-id/<source_doc_id>` | GET | **@login_required + tenant check** (fixed this session) |

**JSON API routes (all `@login_required`):**

| Path | Method | Client filtered | Admin only |
|------|--------|----------------|------------|
| `/api/clients` | GET | No | Yes |
| `/api/clients/<id>` | DELETE | No | Yes |
| `/api/properties` | GET | Yes | No |
| `/api/properties/<id>` | GET | Yes | No |
| `/api/properties/<id>/report` | GET | Yes | No |
| `/api/properties/<id>/download-pack` | POST | Yes | No |
| `/api/documents` | GET | Yes | No |
| `/api/documents/by-id/<id>` | GET | Yes | No |
| `/api/documents/<source_doc_id>` | GET | Yes | No |
| `/api/documents/by-id/<id>/pdf` | GET | Yes | No |
| `/api/documents/by-source/<source_doc_id>/pdf` | GET | Yes | No |
| `/api/documents/upload` | POST | Yes | No |
| `/api/packs` | GET, POST | Yes | No |
| `/api/packs/<id>` | GET, PUT, DELETE | Yes | No |
| `/api/packs/<id>/documents` | POST | Yes | No |
| `/api/packs/<id>/documents/<doc_id>` | DELETE | Yes | No |
| `/api/packs/<id>/reorder` | PUT | Yes | No |
| `/api/packs/<id>/export/zip` | GET | Yes | No |
| `/api/packs/<id>/export/pdf` | GET | Yes | No |
| `/api/compliance` | GET | Yes | No |
| `/api/compliance/report` | GET | Yes | No |
| `/api/compliance/actions/resolve` | POST | Yes | No |
| `/api/compliance/actions/snooze` | POST | Yes | No |
| `/api/compliance/actions/resolved` | DELETE | Yes | Yes |
| `/api/dashboard-stats` | GET | Yes | No |
| `/api/stats` | GET | Yes | No |
| `/api/activity` | GET | Yes | No |
| `/api/chat` | POST | Yes | No |
| `/api/settings/users` | GET | No (global list) | Yes |
| `/api/settings/notifications` | POST | Yes | No |
| `/api/settings/password` | POST | Own user only | No |
| `/admin/clients` | POST | N/A | Yes |
| `/admin/users` | POST | N/A | Yes |
| `/admin/delete-client/<id>` | POST | N/A | Yes |

---

## PIPELINE

1. **Ingest:** Scan or upload → `raw/` (optional `.meta.json`)
2. **Watcher:** `auto_ocr_watch.py` polls `Clients/*/raw/` every 2s → ImageMagick preprocess → OCRmyPDF → DOC folder + `review.json`
3. **AI prefill:** `ai_prefill.py` classifies doc type + extracts fields; writes `completeness_score`, `missing_fields`, `needs_attention`; model `claude-sonnet-4-20250514` (hardcoded default)
4. **Sync:** `sync_single_doc` from `sync_to_portal.py` called after AI prefill — writes to portal.db. No direct portal.db inserts in watcher.
5. **Review:** Operator verifies in ReviewStation; POST `/review` updates JSON + portal.db
6. **Export:** Verified docs → delivery folder + Excel + viewer; triggers full portal sync

**Compliance:** `compliance_engine.evaluate_compliance()` reads latest doc per type via `COALESCE(batch_date, scanned_at, reviewed_at)`; four types (gas, EICR, EPC, deposit).

---

## KNOWN ISSUES

- **12 junk test clients in DB** — must be purged before any demo or real agency onboarding. Real clients: Northgate, Oakwood, Riverside, Ligant, Harlow & Essex.
- **deposit-protection API key mismatch:** `compliance_engine.py` looks for `deposit-protection` but portal.db stores `deposit-protection-certificate`. Properties page has a JS workaround (`deriveDepositFromDocs`) that scans documents for any slug containing "deposit". Needs a proper fix.
- **WinError 2 in pipeline.log** — usually non-fatal; PDF still produced. Often Ghostscript/jbig2 toolchain.
- **Double-write fix untested in practice** — `sync_single_doc` post-prefill path not yet validated with a fresh scan.
- **python-dotenv not installed** — Flask shows yellow `.env` warning on startup. Non-blocking. Fix: `pip install python-dotenv`.
- **`compliance_records` table** — 0 rows, never used. Dead weight. Drop or document as deprecated.
- **`tenants` table** — 0 rows, never used. Either wire it or drop it.
- **Debug mode still on** — `app.run(debug=True, use_reloader=False)`. Werkzeug error pages with tracebacks are shown to users. Should be `debug=False` before any client can access the portal.

---

## DECISIONS LOCKED IN

1. MVP-first; letting/property focus; human verification; per-doc pricing.
2. Capture path: Camo/phone acceptable for MVP.
3. Deploy root is `Desktop\MorphIQ\Product`. Legacy `C:\ScanSystem_v2` is fully abandoned and all references removed.
4. GitHub: private repo at deploy root.
5. Secrets: `ANTHROPIC_API_KEY` from `.env` only — never hardcoded.
6. AI doc-type matching is **contains**-based, not exact string equality.
7. **Portal UX:** Property-first archive + global document search.
8. **portal.db** is SQLite at deploy root. No PostgreSQL.
9. **sync_to_portal.py** is the only bridge from `Clients/` JSON to portal.db.
10. **PDF access in portal:** `/pdf/` and `/pdf-by-id/` routes serve files; both require `@login_required` and tenant scope check (fixed 2026-04-06).
11. **Session Intelligence** panel is browser-only; no watcher changes.
12. **Client scoping** via `?client=` (admins, persisted in session); managers locked to `client_id`.
13. **Compliance rules** live in `compliance_engine.py`; APIs enrich, not duplicate.
14. **Authentication** required for all portal pages/APIs (Flask-Login).
15. **Sync after review** is mandatory for portal freshness (`sync_single_doc`).
16. **Portal IA:** 8-page structure (Overview, Properties, Compliance, Documents, Packs, Ask AI, Reports, Settings). Old routes redirect.
17. **Packs** are client-scoped document collections in portal.db. ZIP and PDF bundle export. Removing from pack does not delete the document.
18. **Documents API** supports server-side search (?q=), type/status filtering, sort. Frontend debounces at 300ms.
19. **Properties API** returns per-property compliance badges and overall status in a single batched query.
20. `Path(__file__).resolve().parent` used for BASE path in all pipeline scripts. No hardcoded deploy root anywhere.
21. **Multi-page documents** use group_id system: `.meta.json` + `.group_complete` marker. Watcher processes group as single DOC.
22. **Watcher syncs via `sync_single_doc` only** — no direct portal.db inserts in `process_file()` or `process_group()`.
23. **Properties page split-panel layout** is canonical (320px left fixed, flex-1 right, 3 tabs: Documents / Compliance timeline / Property info).
24. **Test client "Harlow & Essex Lettings"** is the canonical test dataset — 6 properties, 27 documents, all compliance scenarios.
25. **Flask reloader disabled** (`use_reloader=False`) in app.py — reloader child process caused DATABASE_URL path misresolution leading to `sqlite3.OperationalError`. Fixed 2026-04-06.
26. **User management model:** admin users have `client_id=NULL` and can access all clients. Manager users have a `client_id` and are hard-locked to that client. New users created via `POST /admin/users` with `generate_password_hash`. Users can change their own password via `POST /api/settings/password`.

---

## ACTION ITEMS

1. **Purge 12 junk test clients** from portal.db before any demo or onboarding. Keep: Northgate (11), Oakwood (14), Riverside (15), Ligant (16), Harlow & Essex (28). Delete the rest via Settings → Remove clients, or SQL.

2. **Fix deposit-protection key mismatch** in `compliance_engine.py` — change lookup key from `deposit-protection` to `deposit-protection-certificate` to match what portal.db actually stores. Remove the JS workaround once fixed.

3. **Turn off Flask debug mode** before any client-facing access — change `debug=True` to `debug=False` in `app.py` line 4855. Werkzeug tracebacks must not be visible to clients.

4. **SESSION 2 — Run `generate_test_documents.py`:** creates 27 JPEGs + `.meta.json` for Harlow & Essex Lettings. Stop watcher first. Requires Pillow installed.

5. **SESSION 3 — Run pipeline + `set_test_verification_states.py`:** process through watcher → OCR → AI prefill, set verification states per scenario, run `sync_to_portal.py`.

6. **SESSION 4 — Full 8-page portal verification** against all 6 test properties. Fix remaining issues.

7. Validate **double-write fix** with a fresh real document scan.

8. Run `simulate_multipage.py` to test **multi-page group processing** end-to-end.

9. Connect **Report template "Generate" buttons** to actual endpoints.

10. **Hetzner VPS deployment** — Flask behind Nginx/Gunicorn, HTTPS, Ubuntu 24.04. Not started.

11. **Install python-dotenv:** `pip install python-dotenv` to suppress Flask startup warning.

12. **Scope `GET /api/settings/users`** per client — currently returns all users globally. A manager at Agency A should not see Agency B's users.

---

## OPEN QUESTIONS

- Long-term: keep bundling `viewer.html` in every delivery for offline handoff, or portal-only?
- Add additional compliance types (fire safety, Right to Rent) before first paid client?
- Drop `compliance_records` and `tenants` tables, or document as reserved for future use?

---

## CHANGE LOG

| Date | Summary |
|------|---------|
| 2026-04-06 | **Security + stability + multi-tenant onboarding.** Fixed unauthenticated PDF routes (`/pdf/` and `/pdf-by-id/`) — added `@login_required` and tenant scope check to both (`portal_new/app.py`). Fixed `sqlite3.OperationalError: unable to open database file` on login — `DATABASE_URL` now uses `os.path.normpath()` and Flask reloader disabled (`use_reloader=False`). Removed debug `console.log` leaking AI chat payloads from `portal_new/static/portal.js`. Cleaned all `C:\ScanSystem_v2` stale path references from `scan_station.html`, `portal_new/app.py`, `portal_new/import_fields.py`, `server.py`. Built multi-tenant onboarding: `POST /admin/clients`, `POST /admin/users` (with `generate_password_hash`), `POST /api/settings/password`; updated `GET /api/settings/users` to include `client_name`; Settings page now has Add client form, Add user form (client dropdown), Change password form, Client column in users table — all wired and live. CSS for inline forms added to `portal.css`. |
| 2026-04-03 | Properties page full redesign: split-panel layout, 4-block compliance strip, cert pills, urgency grouping, contextual alert banners, document cards, 3-tab right panel. Session-based client persistence added to `get_current_client()`. `generate_test_documents.py`, `set_test_verification_states.py`, `admin_delete_client.py` created. 4-session test plan defined for Harlow & Essex Lettings. |
| 2026-03-30 | Portal `/properties`: compliance summary strip; list auto-selects first visible property on load. |
| 2026-03-26 | Watcher double-write fix. ReviewStation merge/split built. `simulate_multipage.py` added. |
| 2026-03-25 | ScanStation multi-page capture. Watcher `process_group()` built. AI prefill quality assessment. ReviewStation triage + verification gate. Infrastructure: replaced all `C:\ScanSystem_v2` hardcoded paths with script-relative resolution. |
| 2026-03-24 | Portal wiring phase: Properties API enriched, Documents API wired, Packs built end-to-end, visual polish, IA restructure to 8 pages. Bug fixes: Add-to-Pack modal CSS, Overview JS SyntaxError. |
| 2026-03-23 | Portal `/dashboard` layout; `GET /api/dashboard-stats`. |
| 2026-03-22 | Ops: BitLocker, `.env`, `setup_check.bat`, `rerun_prefill.py`, GitHub. Portal: `/ai-chat`, `/dashboard`, `/archive`. |
| 2026-03-15 | Portal sessions 1–5: auth, search, upload, chat, reports, settings, activity, sidebar, compliance actions. |
