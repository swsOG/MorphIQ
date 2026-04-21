# PROJECT BRAIN — MorphIQ Document Scanning & Compliance Platform

> **Last updated:** 2026-04-21
> **Purpose:** Single source of truth for the current system. Read this before making changes.

---

## READ THIS FIRST

- Start with `docs/CLAUDE_HANDOFF.md` for the fastest current-state summary.
- If anything in this file conflicts with the newer handoff doc or the live code, the newer handoff / code wins.

---

## BUSINESS

**What:** Document scanning and compliance platform for UK letting agencies. Digitises property certificates, extracts compliance data with AI, and provides a client portal for document access and compliance tracking.

**Value prop:** "Not just scanned — understood." Catches missed certificate expiry dates — protects agencies from fines up to £6,000.

**Target:** Letting agencies. Each gets isolated login and isolated client scope inside a shared portal database.

**Name:** Morph IQ. **Status:** Product completion phase. Primary objective is to finish MorphIQ to a trustworthy, demo-ready standard before broader career/marketing work.

### North star

MorphIQ should feel like one coherent product:

1. ScanStation captures the document.
2. ReviewStation checks AI extraction against the source.
3. Only verified documents reach the portal.
4. Clients can challenge a specific delivered document.
5. MorphIQ routes that issue into review rework or re-scan rework.
6. The corrected version only becomes current after re-verification.

### Product model locked in

- One shared `portal.db`, not one database per client.
- `manager` users are restricted to their assigned `client_id`.
- `admin` users can switch client context and manage broader operations.
- General support chat exists, but document complaints create formal issue tickets.
- Challenged documents remain visible with an `Under review` state.
- Corrected documents only replace the current portal version after re-verification.

---

## CURRENT STATE

### 2026-04-21 working truth

This section is the current handoff snapshot and should be treated as higher priority than older bullets lower in the file.

- **Tenant isolation is now materially stronger:** pytest coverage proves manager scoping across list, detail, PDF/download, upload, and compliance-mutation routes. Real cross-client leaks were found and fixed in `/api/documents/upload`, `/api/compliance/actions/resolve`, and `/api/compliance/actions/snooze`.
- **Exception workflow is now first-class in the portal:** `portal_new/app.py` contains structured issue tickets, linked messages, attachments, document-version snapshots, assignment/routing/status APIs, and automatic resolution after re-verification.
- **Portal exception UX is live:** the document page now exposes `Delivery assurance`, `Report a problem`, issue timeline, and support linking; Settings has a dedicated `Support` tab; admins have a dedicated `Issues` workspace.
- **Legacy report-label confusion is fixed:** the property preview action that used to say `Report` while downloading a PDF now says `Export report`, and document cards route users into the proper document-management view.
- **Browser smoke coverage now exists:** `package.json`, `playwright.config.js`, `scripts/start_portal_smoke_server.py`, and `tests/smoke/portal.smoke.spec.js` prove one real browser path end to end: manager logs in, reports a document issue, reaches Support, and admin sees the ticket in `Issues`.
- **Current verification state:** Python regression suite passes (`42 passed`) and browser smoke passes (`npm run test:smoke`).
- **Best next technical/product step:** build the dedicated internal rework experience for re-scan and review teams, then widen browser smoke coverage for support send, issue update, assign/reroute, and mobile flows.

### What works today (confirmed)

- **Full pipeline wired end-to-end:** ScanStation → OCR (ImageMagick + OCRmyPDF + Tesseract) → AI prefill (Gemini default, Anthropic optional) → ReviewStation → sync_to_portal.py → portal.db → portal UI.
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
- **Deposit compliance slug mismatch fixed (2026-04-18):** compliance lookups now use the canonical `deposit-protection-certificate` key used by the portal and seeded data. The property-detail document summary branch now recognizes the same canonical slug consistently.
- **Sync duplicate prevention hardened (2026-04-18):** `sync_to_portal.py` now maps `"Deposit Protection"` to the canonical `deposit-protection-certificate` key, revives soft-deleted rows when a document reappears on disk, and reuses seeded/import placeholders for the same property/type when the real `DOC-*` review folder arrives. This prevents the sync path from recreating duplicate seeded-vs-scanned rows during future seed/import cycles.
- **Sync duplicate prevention verified in live rerun (2026-04-18):** a full `sync_to_portal.py` rerun completed after the fix with 0 active Harlow duplicate groups and 0 active rows on the legacy `deposit-protection` key, so the duplicate-prevention change held in the actual sync path, not just in isolated helper checks.
- **Batch-aware DOC identity enabled (2026-04-18):** generic ScanStation IDs like `DOC-00003` are now stored in `portal.db` as batch-aware values such as `2026-04-18__DOC-00003`, while the portal still strips that prefix when it needs the real folder/PDF path. This stops later Harlow batches from overwriting earlier ones just because they reused the same `DOC-*` folder names.
- **Debug console.log removed (fixed this session):** `portal.js` had `console.log("Chat request:", url, options)` leaking AI chat request payloads to browser DevTools — removed.
- **Stale path references cleaned (this session):** All `C:\ScanSystem_v2` references removed from `scan_station.html`, `portal_new/app.py`, `portal_new/import_fields.py`, `server.py`.
- **`requirements.txt` created (Phase 0):** `Product/requirements.txt` now declares all 10 third-party packages pinned to installed versions: anthropic, flask, flask-cors, flask-login, werkzeug, reportlab, pypdf, pdfminer.six, pdfplumber, openpyxl. System CLIs (ocrmypdf, tesseract, imagemagick) flagged in a comment — not pip-installable.
- **Debug mode gated on env var (Phase 0):** `app.run` now reads `FLASK_DEBUG` env var; defaults off. Werkzeug tracebacks no longer exposed by default. Set `FLASK_DEBUG=1` locally to re-enable.
- **Public marketing domain live (verified 2026-04-18):** `morphiqtechnologies.com` resolves publicly and serves the website. DNS currently points at GitHub Pages IPs, while `Business/Website/index.html` already uses the canonical domain for `og:url`, `<link rel="canonical">`, and Plausible `data-domain`.
- **Working workspace moved out of OneDrive (2026-04-18):** active local path is now `C:\Users\user\Projects\MorphIQ`. This is the canonical working copy for product work; the old OneDrive location should no longer be treated as the real workspace.
- **Watcher path restored in new workspace (2026-04-18):** `auto_ocr_watch.py` is now running against `C:\Users\user\Projects\MorphIQ\Product\Clients\...` and processing raw documents in the moved workspace. `Start_System_v2.bat` and `setup_check.bat` were hardened to resolve a concrete Python executable instead of assuming `python` is on PATH.
- **Gemini prefill path enabled and smoke-tested (2026-04-18):** `ai_prefill.py` now supports provider selection and is configured locally to use Gemini. A real test document (`DOC-00003`) successfully auto-detected as EPC and completed AI extraction through Gemini, so the prefill path is no longer blocked on Anthropic credits.
- **Gemini is now the live default in the actual product copy (2026-04-20):** `C:\Users\user\Projects\MorphIQ\Product\ai_prefill.py` now defaults `get_ai_provider()` to Gemini even when no provider env var is set, which aligns the running code with the current local `.env` setup and removes the previous fallback-to-Anthropic mismatch.
- **Scan-time metadata is preserved again (2026-04-20):** `auto_ocr_watch.py::write_review_json()` now carries `initial_fields` such as `property_address` into `review.json["fields"]` instead of dropping them. This fixes the live data-loss path that caused imported documents to fall back to `Unassigned property` when AI extraction did not refill the address cleanly.
- **Baseline pytest suite now live (2026-04-21):** the live repo now has actual pytest plumbing via `requirements.txt` + `pytest.ini`, and the current pytest baseline covers 10 passing checks across the actual product copy. `tests/test_pipeline_basics.py` covers Gemini-as-default provider selection, provider routing through the Gemini path, `write_review_json()` preserving `initial_fields`, `ensure_property()` reusing the `Unassigned property` placeholder, seeded-row reuse during DOC-folder imports, and duplicate-merge behavior for legacy/prefixed `source_doc_id` rows. `tests/test_portal_auth.py` now covers manager client isolation, admin client switching/session persistence, and access control on `/api/clients`.
- **Portal client picker API is now admin-only (2026-04-21):** `/api/clients` previously allowed any authenticated user to fetch the global client list. It now returns `403 Forbidden` for non-admin users, which closes a cross-tenant information leak and aligns the route with the actual portal UX where only admins use the client picker.
- **Harlow dataset audit completed (2026-04-18):** the current Harlow state in `portal.db` matches the batch folders on disk exactly, so the remaining issue is dataset intent, not sync corruption. There are 100 active Harlow rows across three batches: `2026-04-02` (60 docs, including 35 `new` / `unknown` rows), `2026-04-03` (11 docs, all `new` / `unknown`), and `2026-04-18` (29 docs, which is the regenerated 27-doc canonical set plus 2 extra raw scan docs). This means any cleanup from here is a deliberate demo-data choice, not a required bug fix.
- **Harlow demo dataset pruned cleanly (2026-04-18):** the older Harlow batches `2026-04-02` and `2026-04-03` were deleted, the extra raw scan docs `2026-04-18/DOC-00028` and `DOC-00029` were removed, and a fresh sequential `sync_to_portal.py` rerun pruned 73 stale Harlow records from `portal.db`. Harlow is now back to the intended canonical demo shape: 27 active documents, all from `2026-04-18`.
- **Harlow canonical batch fully AI-prefilled (2026-04-18):** `scripts/rerun_prefill.py` was run against the cleaned Harlow dataset, successfully classifying and extracting the remaining 26 raw docs. After a sequential `sync_to_portal.py` rerun, Harlow now has 27 active `ai_prefilled` documents in `portal.db` with this distribution: 3 deposit protection, 5 EICR, 5 EPC, 6 gas safety certificates, 2 inventory reports, and 6 tenancy agreements.
- **Live demo state changed from Harlow-only to two active clients (2026-04-20):** the running `portal.db` now has 2 active clients: `Harlow & Essex Lettings` and `Epping Lettings`. `Epping Lettings` was imported into the live project copy and synced successfully for portal inspection.
- **Dedicated demo login now points at Epping Lettings (2026-04-20):** `demo@harlowessex.co.uk` remains the manager-scoped demo account in the live database, but its `client_id` now targets `Epping Lettings` so the demo login opens directly into the imported validation dataset instead of the older Harlow baseline.
- **External dependency blocked:** Plausible domain setup cannot be completed directly from this workspace because Sydney controls the domain-side access needed for `morphiqtechnologies.com`.

### Not done / product gaps

- **Packs feature:** `pack_documents` table has 0 rows — packs CRUD API built but not fully exercised end-to-end.
- **Tenants table:** 0 rows — schema exists, never populated. Either wire it or drop it.
- `compliance_records` table: 0 rows — superseded by compliance_actions. Dead weight.
- Archive **scoped export** (filter by status/type from UI) still TODO.
- **Multi-page E2E path verified in the live repo (2026-04-21):** a fresh 2-page simulated capture was injected into `Clients/Epping Lettings/raw`, the watcher consumed the `.group_complete` marker, produced one grouped PDF/review bundle under `Batches/2026-04-21/DOC-00001`, classified it as `Inventory`, and synced it into `portal.db` as `2026-04-21__DOC-00001` with extracted fields and real property assignment.
- **Baseline automated tests now meet the initial Week 1 bar:** the live repo has working pytest plumbing plus 10 passing baseline tests across `ai_prefill`, `auto_ocr_watch`, `sync_to_portal`, and portal auth/client scoping. Follow-up test work should now focus on broadening coverage rather than first-time setup.
- **Hetzner VPS deployment** — not started.
- **Password reset by email** — deferred until Hetzner (needs SMTP).
- **python-dotenv not installed** — Flask shows yellow warning. Non-blocking. Fix: `pip install python-dotenv`.

---

## DATABASE

**File:** `portal.db` at project root (`C:\Users\user\Projects\MorphIQ\Product\portal.db`)

**Tables (13):**
`activity_log`, `clients`, `compliance_actions`, `compliance_records`, `document_fields`, `document_types`, `documents`, `pack_documents`, `packs`, `properties`, `sqlite_sequence`, `tenants`, `users`

**Live counts (queried 2026-04-20):**

| Table | Rows | Notes |
|---|---|---|
| `clients` | 2 | Active clients in live demo DB: Harlow & Essex Lettings, Epping Lettings |
| `properties` | 13 | |
| `documents` | 54 | |
| `document_fields` | 339 | |
| `users` | 2 | |
| `compliance_actions` | 24 | |
| `compliance_records` | 0 | Superseded — dead weight |
| `tenants` | 0 | Schema only — never populated |
| `pack_documents` | 0 | Packs feature incomplete |
| `packs` | 1 | |
| `document_types` | 8 | |

**Clients (2 active):**

Harlow & Essex Lettings (id=28), Epping Lettings (id=30)

**Users (3):**

| id | email | role | client_id |
|---|---|---|---|
| 1 | filip@morphiq.co.uk | admin | NULL |
| 2 | demo@harlowessex.co.uk | manager | 30 (Epping Lettings) |

---

## SYSTEM ARCHITECTURE

**Deploy root:** `C:\Users\user\Projects\MorphIQ\Product`

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
3. **AI prefill:** `ai_prefill.py` classifies doc type + extracts fields; writes `completeness_score`, `missing_fields`, `needs_attention`; Gemini is the live default provider and Anthropic remains an optional path.
4. **Sync:** `sync_single_doc` from `sync_to_portal.py` called after AI prefill — writes to portal.db. No direct portal.db inserts in watcher.
5. **Review:** Operator verifies in ReviewStation; POST `/review` updates JSON + portal.db
6. **Export:** Verified docs → delivery folder + Excel + viewer; triggers full portal sync

**Compliance:** `compliance_engine.evaluate_compliance()` reads latest doc per type via `COALESCE(batch_date, scanned_at, reviewed_at)`; four types (gas, EICR, EPC, deposit).

---

## KNOWN ISSUES

- **12 junk test clients in DB** — must be purged before any demo or real agency onboarding. Real clients: Northgate, Oakwood, Riverside, Ligant, Harlow & Essex.
- **WinError 2 in pipeline.log** — usually non-fatal; PDF still produced. Often Ghostscript/jbig2 toolchain.
- **Graceful AI-provider fallback is still not productized:** Gemini is now the default path, but upstream provider/API failures still need a clearer manual-attention fallback state in the product.
- **Anthropic API credits exhausted** — no longer the active pipeline path because local prefill is now configured to use Gemini instead. This only matters if the product is switched back to Anthropic later.
- **python-dotenv not installed** — Flask shows yellow `.env` warning on startup. Non-blocking. Fix: `pip install python-dotenv`.
- **`compliance_records` table** — 0 rows, never used. Dead weight. Drop or document as deprecated.
- **`tenants` table** — 0 rows, never used. Either wire it or drop it.

---

## DECISIONS LOCKED IN

1. MVP-first; letting/property focus; human verification; per-doc pricing.
2. Capture path: Camo/phone acceptable for MVP.
3. Deploy root is `C:\Users\user\Projects\MorphIQ\Product`. Legacy `C:\ScanSystem_v2` is fully abandoned and all references removed.
4. GitHub: private repo at deploy root.
5. Secrets: provider API keys come from `.env` only — never hardcoded.
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
27. **Canonical domain:** `morphiqtechnologies.com`. `morphiq.co.uk` is abandoned. OG URL, canonical meta, and Plausible `data-domain` in `Business/Website/index.html` all updated.

---

## ACTION ITEMS

1. **Purge 12 junk test clients** from portal.db before any demo or onboarding. Keep: Northgate (11), Oakwood (14), Riverside (15), Ligant (16), Harlow & Essex (28). Delete the rest via Settings → Remove clients, or SQL.

2. **Fix deposit-protection key mismatch** in `compliance_engine.py` — change lookup key from `deposit-protection` to `deposit-protection-certificate` to match what portal.db actually stores. Remove the JS workaround once fixed.

3. **SESSION 2 — Run `generate_test_documents.py`:** creates 27 JPEGs + `.meta.json` for Harlow & Essex Lettings. Stop watcher first. Requires Pillow installed.

4. **SESSION 3 — Run pipeline + `set_test_verification_states.py`:** process through watcher → OCR → AI prefill, set verification states per scenario, run `sync_to_portal.py`.

5. **SESSION 4 — Full 8-page portal verification** against all 6 test properties. Fix remaining issues.

6. Validate **double-write fix** with a fresh real document scan.

7. Run `simulate_multipage.py` to test **multi-page group processing** end-to-end.

8. Connect **Report template "Generate" buttons** to actual endpoints.

9. **Hetzner VPS deployment** — Flask behind Nginx/Gunicorn, HTTPS, Ubuntu 24.04. Not started.

10. **Install python-dotenv:** `pip install python-dotenv` to suppress Flask startup warning.

11. **Scope `GET /api/settings/users`** per client — currently returns all users globally. A manager at Agency A should not see Agency B's users.

---

## OPEN QUESTIONS

- Long-term: keep bundling `viewer.html` in every delivery for offline handoff, or portal-only?
- Add additional compliance types (fire safety, Right to Rent) before first paid client?
- Drop `compliance_records` and `tenants` tables, or document as reserved for future use?

---

## CHANGE LOG

| Date | Summary |
|------|---------|
| 2026-04-21 | **Portal auth/scoping baseline strengthened.** Added `tests/test_portal_auth.py` to cover manager client isolation, admin client switching/session persistence, and `/api/clients` access control in an isolated temp-db app instance. Fixed `/api/clients` so it is admin-only, then verified the full live pytest baseline with `python -m pytest Product/tests -q` → 10 passed. |
| 2026-04-21 | **Live multi-page E2E verification passed.** Started the live watcher, injected a controlled 2-page simulated document into `Epping Lettings/raw` using `scripts/simulate_multipage.py`, and verified the full path end to end: watcher consumed the group marker, OCR completed, Gemini classified the grouped PDF as `Inventory`, `review.json` captured `group_id`/`page_count` plus extracted fields, and `portal.db` gained one new `ai_prefilled` row (`2026-04-21__DOC-00001`) mapped to property `146 Cromwell Street, Waltham Abbey, EN9 5HC`. |
| 2026-04-21 | **Pytest baseline completed.** Added `pytest==8.4.2` to `requirements.txt`, created `pytest.ini`, and verified the live baseline suite with `python -m pytest Product/tests -q` → 6 passed. The Week 1 “pytest + initial 5–10 baseline tests” task is now complete in the running repo. |
| 2026-04-20 | **Live pipeline and memory re-aligned.** Fixed `auto_ocr_watch.py` so scan-time `initial_fields` survive into `review.json`, switched the live `ai_prefill.py` default provider to Gemini, expanded `tests/test_pipeline_basics.py` to 6 passing checks across provider routing and sync logic, imported `Epping Lettings` into the live project copy, repointed the demo manager login to that client, and updated Notion/task state plus this project brain to match the actual running repo. |
| 2026-04-18 | **Batch-aware DOC identity fixed.** Updated `sync_to_portal.py` so reused ScanStation IDs are stored as batch-aware values like `2026-04-18__DOC-00003`, and updated the portal PDF helper to strip that prefix back to the real folder name when opening ScanStation files. A live rerun left Harlow with 100 active prefixed rows, 0 active raw `DOC-*` rows, and separate active records for repeated IDs across `2026-04-02`, `2026-04-03`, and `2026-04-18`. |
| 2026-04-18 | **Gemini prefill enabled.** Added Gemini support to `ai_prefill.py`, created local `.env` / `.env.example` provider config, and smoke-tested the switch on `DOC-00003`: auto-detection classified the document as EPC and extraction completed successfully through Gemini. |
| 2026-04-18 | **Anthropic blocker classified correctly.** Confirmed the AI prefill failure is an upstream billing/credit issue rather than a watcher/path bug. Marked the prefill task blocked in Notion and added a follow-up task to improve graceful fallback behavior when AI credits or API availability fail. |
| 2026-04-18 | **Watcher startup restored.** Hardened `Start_System_v2.bat` and `setup_check.bat` to resolve Python explicitly, then started `auto_ocr_watch.py` successfully from `C:\Users\user\Projects\MorphIQ\Product`. The watcher is now processing raw documents in the new workspace again. |
| 2026-04-18 | **Template set completed.** Added `Product/Templates/deposit_protection_certificate.json` and `Product/Templates/inventory.json` using the same field structure already expected by `ai_prefill.py`, so the template folder now covers the full supported document set. |
| 2026-04-18 | **Deposit compliance alignment.** Fixed the deposit compliance lookup to use the canonical `deposit-protection-certificate` slug in `portal_new/compliance_engine.py`, and updated the property-detail summary branch in `portal_new/app.py` to recognize the same canonical slug consistently. |
| 2026-04-18 | **Workspace and planning alignment.** Moved the active MorphIQ working copy out of OneDrive to `C:\Users\user\Projects\MorphIQ`, confirmed this is now the canonical product workspace, and explicitly re-centered the project on finishing MorphIQ as the product before broader career/marketing tasks. Plausible domain setup remains blocked on Sydney/domain-side access. |
| 2026-04-18 | **Phase 0 — safety + reproducibility (Cursor).** Created `Product/requirements.txt` (10 packages, pinned). Gated `debug=True` on `FLASK_DEBUG` env var (defaults off). Deleted `.cursor/debug-c11422.log`. Produced `MORPHIQ_AUDIT.md` (14-section codebase audit, verdict: refactor) and `WEBSITE_AUDIT.md` (7-section site audit). Canonicalised domain to `morphiqtechnologies.com` across `Business/Website/`, then verified the public domain resolves and serves the live marketing site. |
| 2026-04-06 | **Security + stability + multi-tenant onboarding.** Fixed unauthenticated PDF routes (`/pdf/` and `/pdf-by-id/`) — added `@login_required` and tenant scope check to both (`portal_new/app.py`). Fixed `sqlite3.OperationalError: unable to open database file` on login — `DATABASE_URL` now uses `os.path.normpath()` and Flask reloader disabled (`use_reloader=False`). Removed debug `console.log` leaking AI chat payloads from `portal_new/static/portal.js`. Cleaned all `C:\ScanSystem_v2` stale path references from `scan_station.html`, `portal_new/app.py`, `portal_new/import_fields.py`, `server.py`. Built multi-tenant onboarding: `POST /admin/clients`, `POST /admin/users` (with `generate_password_hash`), `POST /api/settings/password`; updated `GET /api/settings/users` to include `client_name`; Settings page now has Add client form, Add user form (client dropdown), Change password form, Client column in users table — all wired and live. CSS for inline forms added to `portal.css`. |
| 2026-04-03 | Properties page full redesign: split-panel layout, 4-block compliance strip, cert pills, urgency grouping, contextual alert banners, document cards, 3-tab right panel. Session-based client persistence added to `get_current_client()`. `generate_test_documents.py`, `set_test_verification_states.py`, `admin_delete_client.py` created. 4-session test plan defined for Harlow & Essex Lettings. |
| 2026-03-30 | Portal `/properties`: compliance summary strip; list auto-selects first visible property on load. |
| 2026-03-26 | Watcher double-write fix. ReviewStation merge/split built. `simulate_multipage.py` added. |
| 2026-03-25 | ScanStation multi-page capture. Watcher `process_group()` built. AI prefill quality assessment. ReviewStation triage + verification gate. Infrastructure: replaced all `C:\ScanSystem_v2` hardcoded paths with script-relative resolution. |
| 2026-03-24 | Portal wiring phase: Properties API enriched, Documents API wired, Packs built end-to-end, visual polish, IA restructure to 8 pages. Bug fixes: Add-to-Pack modal CSS, Overview JS SyntaxError. |
| 2026-03-23 | Portal `/dashboard` layout; `GET /api/dashboard-stats`. |
| 2026-03-22 | Ops: BitLocker, `.env`, `setup_check.bat`, `rerun_prefill.py`, GitHub. Portal: `/ai-chat`, `/dashboard`, `/archive`. |
| 2026-03-15 | Portal sessions 1–5: auth, search, upload, chat, reports, settings, activity, sidebar, compliance actions. |

---

## SESSION MEMORY UPDATE - 2026-04-18

- `portal.db` test-data cleanup is now complete. Verification after cleanup confirmed:
  - 0 active `unknown` documents
  - 0 active duplicate property/type groups
  - 0 active document paths still pointing at the old OneDrive root
- Cleanup was executed via `scripts/cleanup_test_documents.py`. The script:
  - migrated active `pdf_path` / `raw_image_path` values from the old OneDrive root to `C:\Users\user\Projects\MorphIQ\Product` where files existed
  - remapped legacy `deposit-protection` document rows to `deposit-protection-certificate`
  - reclassified supported `unknown` test docs from filename/doc-name heuristics
  - soft-deleted unsupported synthetic bulk-import rows
  - soft-deleted superseded duplicate property/type rows
- New follow-up discovered during cleanup:
  - `sync_to_portal.py` can still recreate duplicate seeded/import rows because it keys identity on `(source_doc_id, client_id)` and still carries the legacy `"Deposit Protection" -> deposit-protection` mapping
  - treat that as the next data-integrity prevention task before relying on repeated seed/import cycles
- Provider state reminder:
  - local AI prefill is now running through Gemini via env config
  - Anthropic is optional and no longer the default assumption for this project state
- Workflow state reminder:
  - Codex now follows a repo-first authority order: repo/workspace/runtime -> `PROJECT_BRAIN.md` -> Notion tracker -> execution plan
  - the execution plan remains the strategic north star, but Notion plus repo reality drive day-to-day task selection
  - autonomous heartbeat execution is allowed for straightforward work; Codex pauses only on real forks with options and a recommendation
  - new-thread continuity now uses `CODEX_STARTUP_PROTOCOL.md` and `CODEX_EXECUTION_LOG.md` so Codex can resume from a clean handoff instead of relying on chat memory alone

## SESSION MEMORY UPDATE - 2026-04-18 (AUTOMATION)

- Implemented the MorphIQ autonomous workflow system for Codex.
- Added `CODEX_AUTOMATION_POLICY.md` at the project root as the durable policy note for future sessions and heartbeat runs.
- Updated `COWORK_CONTEXT.md` so Codex-only workflow now uses:
  - repo/workspace/runtime -> brain -> Notion -> execution plan authority order
  - execution-plan-as-strategy rather than execution-plan-as-queue
  - automatic execution for straightforward tasks
  - pause only on real forks with options and a recommendation
- Added `CODEX_STARTUP_PROTOCOL.md` to define the exact read order for any new thread or heartbeat wake-up.
- Added `CODEX_EXECUTION_LOG.md` as the lightweight continuity and handoff log. New threads should read the latest log entry before choosing work.
- Tightened the automation policy with:
  - a strict definition of done
  - verification rules by task risk
  - a blocked-task policy
  - an explicit requirement to update the execution log after meaningful work
- Upgraded decision handling for real forks:
  - every pause now requires a dual-layer decision brief
  - the brief must include both a technical explanation and a plain-English project-specific explanation
  - a concrete MorphIQ example should be included whenever it helps the decision make immediate sense
- Prepared this thread to run as the autonomous control loop for MorphIQ work.
- Packs workflow is now upgraded from placeholder state to usable MVP:
  - dedicated `/packs` page now supports adding documents from the current client
  - dedicated `/packs` page now supports drag/drop reorder with save
  - backend pack insertion now filters to valid current-client docs and skips duplicates already in the pack
  - next check is live browser QA on create/add/reorder/export using the Harlow demo account
- Packs add-documents UX is now property-first:
  - the add modal now opens into property folders instead of a flat list
  - live search filters properties by address and documents within the active property view
  - the modal now uses the proper ATP layout/scroll classes and a wider browser-style layout
  - `available-documents` now returns `property_id` so grouping stays reliable client-side
- Sync/import has been hardened against legacy duplicate recreation:
  - sync now recognizes legacy raw `DOC-*` ids and newer batch-prefixed ids as the same document
  - duplicate document rows are merged onto one canonical record during sync
  - dependent `document_fields` and `pack_documents` are preserved when duplicates/stale docs are removed
  - verified on the Harlow baseline: rerun stayed at 27 docs, 166 fields, and 0 duplicate `source_doc_id`s
- Review workflow now has an in-portal approval path:
  - document cards/list rows now expose a direct `Review` or `View` action into the document viewer
  - the document viewer now shows `Mark Verified` for reviewable statuses instead of forcing a separate ReviewStation jump
  - portal verification writes back to `review.json`, resyncs that single document into `portal.db`, and records the activity event
  - the properties page now uses that same portal review route instead of linking to the old ReviewStation screen
  - next check is one real browser verification on a Harlow `ai_prefilled` document to confirm the status refresh feels smooth
