# PROJECT BRAIN — ScanStation Document Archiving System

> **Last updated:** 2026-04-03
> **Purpose:** Single source of truth for the current system. Read this before making changes.

---

## BUSINESS

**What:** Local document scanning and digital archiving for letting agencies and landlords (Harlow, Essex; corridor expansion planned).

**Value prop:** “Not just scanned — understood.” Searchable PDFs, verified key fields, organised delivery, human verification—not raw OCR only.

**Differentiator:** Per-document pricing with verified field extraction vs generic per-page scanning.

**Name:** Morph IQ (landing page exists; not live). **Gaps:** No paying clients yet; pricing not final; GDPR/commercial paperwork not done; outreach not started.

---

## CURRENT STATE

### Working (authoritative)

- **Pipeline:** ImageMagick → OCRmyPDF + Tesseract → searchable PDF; watcher polls `Clients/*/raw/` every 2s, creates `Batches/date/DOC-XXXXX`, runs AI prefill after each new doc, supports `.meta.json` and `.reprocess` in place. Watcher double-write fix applied: direct portal.db inserts removed from both `process_file()` and `process_group()`. After AI prefill completes (or is skipped), `sync_single_doc` from `sync_to_portal.py` is called to sync the review.json data into portal.db. This matches the pattern used by ReviewStation's POST `/review`. Documents now appear in the portal with correct classification immediately after watcher processing — no manual `sync_to_portal.py` run needed.
- **ScanStation** (`scan_station.html`): Capture, session queue, rescan flow, Export/Open Portal, camera settings (MediaStream), Live Session Intelligence panel (client-side counts only). ScanStation supports **multi-page document capture**: 'Add Page' button + `P` keyboard shortcut groups multiple scanned pages into a single document. State tracks isMultiPage, groupId (timestamp-based `grp_` prefix), pageNumber, groupDocName. Each page's `.meta.json` includes group_id, page_number, total_pages_so_far. Page 1's meta retroactively updated when 'Add Page' first pressed. Groups completed by: new capture (auto-closes group), 'Finish Document' button, or Escape. Completion writes `<group_id>.group_complete` marker to `raw/`. Session queue shows grouped pages indented with '↳ Page N'. Multi-page indicator bar shows current page and doc name. Single-page capture unchanged.
- **ReviewStation** (`review_station.html`): Dashboard, review with PDF/OCR text, status workflow, rescan reasons, Enter-to-save fields without advancing, Open Portal, auto-sync to portal on save. ReviewStation now includes **triage and validation**: documents with `needs_attention=true` display an amber warning dot in the document list and sort to the top. Fields listed in `missing_fields` are highlighted with an amber left border and 'AI could not extract — please fill manually' label. **Verification gate**: reviewers cannot mark a document as Verified if property_address is empty — an inline error message blocks the action. **Merge/Split capability:** Reviewers can select 2+ documents from the list and click 'Merge Selected' to combine them into one multi-page document (PDFs merged via pypdf, first DOC folder retained, others cleaned up, AI prefill re-run, portal synced). Multi-page documents show a 'Split Pages' button in detail view — splits each page into a separate DOC record (individual PDFs extracted, new DOC folders created, AI prefill per page, portal synced). Both operations show confirmation dialogs. API endpoints: POST `/merge/<client>` (body: {doc_ids: [...]}), POST `/split/<client>/<doc_id>` in server.py.
- **API** (`server.py`, `http://127.0.0.1:8765`): Clients, docs, review, PDF, export, delivery, rescan, OCR text; CORS for `file://`; POST `/review` calls `sync_single_doc`; POST `/export` runs export + full portal re-sync.
- **Export** (`export_client.py`): Verified docs → delivery folder, Excel, `archive_data.json`, embedded `viewer.html`.
- **Viewer** (`viewer.html`): Delivery archive browser; PDF.js + search when served over HTTP.
- **AI prefill** (`ai_prefill.py`): Claude classification when type unknown; six doc types with dedicated prompts; fuzzy “contains” matching; `ANTHROPIC_API_KEY` from `.env` / environment (not committed in batch files). **`rerun_prefill.py`:** batch re-invokes `ai_prefill.py` for `Batches/**/DOC-*` with `review.json` still New or unknown type; watcher-style subprocess + 429 retries; deploy root from script path. AI prefill now includes **completeness scoring**: after field extraction, each document gets a `completeness_score` (0-100%), `missing_fields` (list of empty required field keys), and `needs_attention` flag (true if property_address is empty or completeness_score < 70%) written into review.json. Required fields are defined per document type: Gas Safety (property_address, engineer_name, gas_safe_reg, inspection_date, expiry_date, result), EICR (property_address, electrician_name, inspection_date, next_inspection_date, result), EPC (property_address, current_rating, assessment_date, expiry_date), Tenancy Agreement (property_address, tenant_full_name, start_date, monthly_rent_amount), Deposit Protection (property_address, tenant_name, deposit_amount, protection_date), Inventory (property_address, inspection_date). Unknown doc types get completeness_score=0, needs_attention=true.
- **Portal** (`portal_new/`): Flask-Login; admin vs manager (`client_id`); **8-page IA** with sidebar: Overview, Properties, Compliance, Documents, Packs, Ask AI | Reports, Settings. Routes: `/overview` (compliance score ring, status cards, cert coverage bars, expiry timeline 30/60/90, recent activity, packs quick-access), `/properties` (split-panel: list left with search, filter, cert badges; **auto-selects first visible property** on load and when filter/search changes; detail: **compliance strip** with per-cert status dots, doc counts, click to filter document cards by type or All; doc-type tabs + cards, Add to Pack/Download PDF), `/compliance` (risk banner with fine exposure calc, filter chips with counts, matrix table property × cert type, overall status column), `/documents` (search bar, type/status filter pills, sort + grid/list toggle, document card grid with key fields), `/packs` (split-panel: pack list left, pack builder right with doc rows + reorder + export ZIP/PDF), `/ask-ai` (welcome screen + suggested queries, chat bubbles, pinned input bar with doc count), `/reports` (report template cards, recent reports table, audit trail from activity_log), `/settings` (sub-nav: Team & users + Notifications + Permissions, user table from /api/settings/users, workspace config). Old routes redirect: /dashboard→/overview, /archive→/properties, /activity→/reports, /ai-chat→/ask-ai. **Wiring (live data connections):** Properties API enriched with per-property compliance breakdown (gas/eicr/epc/deposit status + expiry dates), overall_status (compliant/at_risk/non_compliant), doc_count, tenant_name — batched query, no N+1. Documents API supports server-side search (?q=), type filtering (?type=), status filtering (?status=), sorting (?sort=recent|property|type) with debounced frontend. Packs feature fully wired: `packs` + `pack_documents` tables, full CRUD API (GET/POST/PUT/DELETE /api/packs, document add/remove/reorder), "Add to Pack" modal in base.html available on Properties + Documents pages, pack export as ZIP (zipfile) and PDF bundle (ReportLab cover + pypdf merge). Portal Properties page: 'Unassigned property' entries show a 'Needs review — missing property address' subtitle in the left panel and an info banner in the right panel explaining the issue and directing users to ReviewStation. **Session-based client persistence:** `get_current_client()` in app.py stores client name in Flask session (`session["selected_client"]`) when a `?client=` URL param is present; subsequent navigations without the param read from session. This fixes client context loss for clients with `&` in their name (e.g. "Harlow & Essex Lettings") which was truncating the URL param at `&`. **Properties detail panel compliance strip fixed:** `renderDetail()` in `properties.html` now correctly calls `renderDetail(data.property)` (was `renderDetail(data)`) — the API returns `{property: {...}, documents: [...]}` so top-level compliance fields (`gas_safety`, `eicr`, `epc`, `deposit`) were unreachable, showing all certs as "Not on file".
- **Properties page full redesign (2026-04-03):** Split-panel layout — 320px fixed left panel + flex-1 right panel. **Left panel:** search input; filter chips (All / Urgent / At risk / Compliant); properties grouped by urgency with section labels ("Needs immediate action" / "At risk" / "Compliant"); each row shows address, urgency dot, tenant + doc count + postcode, cert pills (GAS / EICR / EPC / DEP) with status colours (red=expired, amber=expiring-soon, teal=compliant, dashed=missing, purple=AI prefilled unverified), coloured left border per urgency state. **Right panel:** full address header + tenant/client/rent subtitle + action buttons (Export pack / Report / Add document); 4-block compliance strip (Gas Safety / EICR / EPC / Deposit — each showing status, value, and date with correct colour state); three tabs: **Documents** (contextual alert banner — red for expired, amber for expiring-soon, hidden when compliant; document cards grouped by type with type tag, trust badge verified/AI prefilled/needs attention, scan date, extracted fields in 3-column grid, action row View PDF / Download / Add to pack / fourth contextual action; missing doc types as dashed placeholder cards), **Compliance timeline** (SVG score ring, cert-by-cert timeline table with status badges), **Property info** (3-section label/value grid: property details / current tenancy / document summary).
- **Portal wiring target (Session 1):** compliance strip reads real data from `/api/properties/<id>`; cert pills reflect actual `compliance_engine` output; document cards render real documents from `document_fields` table; alert banner logic tied to actual compliance state; urgency grouping driven by real DB status. `renderDetail(data.property)` fix applied (was `renderDetail(data)`) — pending full verification against live test data.
- **Sync** (`sync_to_portal.py`): CLI + automatic single-doc and export-time full sync; prunes stale rows; `cleanup_empty_properties`.
- **Ops:** `Start_System_v2.bat` starts watcher + API + portal (loads secrets from `.env`); `User_Guide/` present; `setup_check.bat` validates core deps via `%~dp0`-relative paths (not pdfplumber / flask-login / anthropic); `bulk_import.py` (stdlib-only) stress-feeds numbered `.jpg` into `Clients/*/raw/` for B–E runs. BitLocker enabled on dev machine (March 2026).

### Not done / product gaps

- Deposit Protection + Inventory **templates** not in `Templates/` (export/general still use placeholders where applicable).
- Operator “portal quickstart” doc not written.
- Archive **scoped export** (filter by status/type from UI) still TODO.
- **Multi-page E2E test not completed** — `simulate_multipage.py` script created to test group processing without a camera (simulates ScanStation's .meta.json + .group_complete marker output). Watcher `process_group()` and ReviewStation merge/split are built but not yet validated end-to-end with real or simulated multi-page captures.
- **Full 10-document E2E test** not yet run — blocked until multi-page E2E is validated and double-write fix is confirmed working in practice.
- **Portal wiring fix (Session 1):** compliance strip and cert pills showing “Not on file” even when documents exist in portal.db — `renderDetail` fix applied but not yet verified against live test data. Session 1 will audit and confirm.
- **`generate_test_documents.py`** — script created; 27 JPEGs generated and placed in `Clients/Harlow & Essex Lettings/raw/`. Full pipeline run (watcher → OCR → AI prefill) not yet confirmed clean.
- **`set_test_verification_states.py`** — script created; direct portal.db write run. Full 6-property E2E verification against portal UI not yet confirmed.
- **Full 6-property portal E2E test** not yet run — requires Session 1 wiring fix confirmed, then Sessions 2–4 per test plan.

### Known issues

- **WinError 2** in `pipeline.log` during OCR—usually non-fatal; PDF still produced (often Ghostscript/jbig2 toolchain). **Ghostscript** optional on PATH; OCRmyPDF may warn without it.
- **Stale pack record:** `packs` table may contain a row named after the client (e.g. "Northgate Properties") created accidentally during wiring — delete via SQL or UI once a delete-pack action is wired.
- **Double-write fix untested in practice** — sync_single_doc post-prefill path not yet validated with a fresh scan (portal correctness without manual sync).
- **Watcher / test-data competition:** if `auto_ocr_watch.py` is running when `generate_test_documents.py` drops JPEGs into `raw/`, the watcher will consume and classify them as "Unknown" before `set_test_verification_states.py` runs. Always stop the watcher before generating test data, or use `set_test_verification_states.py` to write directly to DB (bypasses watcher entirely).
- **deposit-protection API key mismatch:** `compliance_engine.py` looks for doc_type key `deposit-protection` but portal.db stores `deposit-protection-certificate`. The detail panel in properties.html has a JS workaround (`deriveDepositFromDocs`) that scans documents for any slug containing "deposit" when the API compliance object shows `missing`. The list panel reads correctly from the enriched list API response.
- **Properties page compliance strip shows "Not on file"** for all cert types regardless of actual document state in portal.db — `renderDetail(data)` → `renderDetail(data.property)` fix applied this session; not yet verified against live test data. Session 1 will confirm.
- **python-dotenv not installed** — Flask shows yellow warning on startup: "Tip: There are .env files present. Install python-dotenv to use them." Non-blocking. Fix: `pip install python-dotenv --break-system-packages`.

---

## SYSTEM ARCHITECTURE

**Deploy root:** `C:\Users\user\OneDrive - University of East London\Desktop\MorphIQ\Product` (Desktop\MorphIQ\Product, OneDrive-synced). **Batch files** use `%~dp0` (directory of the script), so paths are **relative to the script location**—no hardcoded drive root in `.bat` files; Python resolves `BASE` the same way from each script.

**Core layout:**

```
C:\Users\user\OneDrive - University of East London\Desktop\MorphIQ\Product\
├── auto_ocr_watch.py, server.py, export_client.py, sync_to_portal.py, ai_prefill.py
├── scan_station.html, review_station.html, viewer.html
├── Start_System_v2.bat, Stop_System.bat, Stop_Watcher.bat, setup_check.bat
├── bulk_import.py, rerun_prefill.py   # optional: synthetic load; batch AI prefill re-run
├── generate_test_documents.py         # Pillow JPEG generator — 27 A4 docs, 6 properties, "Harlow & Essex Lettings"
├── set_test_verification_states.py    # Direct portal.db writer — inserts client/properties/docs bypassing watcher
├── admin_delete_client.py             # Utility to hard-delete a client and all related rows from portal.db
├── portal_new\          # Flask portal (app.py, templates/, static/)
├── Clients\<Client>\     # raw\, Batches\, Exports\, Logs\
├── Templates\           # JSON field templates (5 + general)
├── portal.db            # SQLite (gitignored)
├── PROJECT_BRAIN.md, SETUP_GUIDE.md, User_Guide\
```

**Legacy:** Older `portal/` Flask UI exists; **portal_new is canonical**. Pipeline and ReviewStation do not depend on it.

---

## API ENDPOINTS

### ScanStation API (`server.py`) — port **8765**

| Method | Path | Role |
|--------|------|------|
| GET | `/health` | Liveness |
| GET | `/clients` | List client folder names |
| GET | `/docs/<client>` | All documents + review payload |
| GET | `/stats/<client>` | Counts by status |
| POST | `/review/<client>/<doc_id>` | Save review → `sync_single_doc` |
| GET | `/pdf/<client>/<doc_id>` | **Canonical PDF** for all UIs |
| GET | `/ocr-text/<client>/<doc_id>` | pdfminer text |
| POST | `/export` | Export + `sync_portal_for_clients` |
| POST | `/open-folder` | Open path under BASE |
| GET | `/delivery/<client>/<export>/<path>` | Serve export files |
| GET | `/raw-image/<client>/<fn>`, `/raw-list/<client>` | Raw inbox |
| GET | `/doc-image/<client>/<doc_id>` | Thumb image in DOC folder |
| POST | `/reprocess/<client>/<doc_id>` | Rescan request |
| POST | `/rescan-replace/<client>/<doc_id>` | Replace scan |
| GET | `/rescan-queue/<client>`, `/exports/<client>` | Queues / history |

CORS: `origins=["null"]` for `file://` HTML.

### portal_new (`portal_new/app.py`) — port **5000**

All HTML/API except login/logout use `@login_required`.

**Pages:** `GET /overview`, `/properties`, `/compliance`, `/documents`, `/packs`, `/ask-ai`, `/reports`, `/settings`, `/property/<id>`; `GET/POST /login`, `GET /logout`. Old routes redirect: `/` → `/overview`, `/dashboard` → `/overview`, `/archive` → `/properties`, `/activity` → `/reports`, `/ai-chat` → `/ask-ai`.

**JSON API (representative):** `GET /api/clients`, `DELETE /api/clients/<id>`, `GET /api/properties[?client=]`, `GET /api/properties/<id>`, `POST /api/properties/<id>/download-pack`, `GET /api/properties/<id>/report`, `GET /api/documents`, `GET /api/documents/<source_doc_id>`, `GET /api/documents/by-id/<id>`, `GET /api/documents/by-id/<id>/pdf`, `GET /api/documents/by-source/<source_doc_id>/pdf`, `POST /api/documents/upload`, `GET /api/compliance`, `GET /api/dashboard-stats`, `POST /api/compliance/actions/resolve`, `POST /api/compliance/actions/snooze`, `DELETE /api/compliance/actions/resolved` (admin), `GET /api/compliance/report`, `POST /api/chat`, `GET /api/activity`, `GET /api/settings/users`, `POST /api/settings/notifications` (placeholder), `GET /api/packs`, `POST /api/packs`, `GET /api/packs/<id>`, `PUT /api/packs/<id>`, `DELETE /api/packs/<id>`, `POST /api/packs/<id>/documents`, `DELETE /api/packs/<id>/documents/<doc_id>`, `PUT /api/packs/<id>/reorder`, `GET /api/packs/<id>/export/zip`, `GET /api/packs/<id>/export/pdf`.

**DB:** `portal.db` — clients, document_types (`key`/`label`), properties (`address`), documents, document_fields, tenants, compliance_records, `users`, `compliance_actions`, `activity_log`, `packs` (id, client_id, name, notes, created_by, created_at, updated_at), `pack_documents` (id, pack_id, document_id, sort_order, added_at) (see `app.py` migrations).

---

## PIPELINE

1. **Ingest:** Scan or upload → `raw/` (optional `.meta.json` consumed by watcher).
2. **Watcher:** Stable file → preprocess (ImageMagick) → OCRmyPDF → DOC folder + `review.json` (`Unknown` → AI prefill).
3. **AI prefill:** Classify + extract fields; `status` → `ai_prefilled` when successful.
4. **Review:** Operator verifies in ReviewStation; POST `/review` updates JSON + `portal.db`.
5. **Export:** Verified-only package + Excel + viewer; optional full portal sync.
6. **Rescan:** `/reprocess` → queue → ScanStation replace → `.reprocess` → watcher re-OCRs same folder.

**Compliance:** `compliance_engine.evaluate_compliance()` reads latest doc per type via `COALESCE(batch_date, scanned_at, reviewed_at)`; four types (gas, EICR, EPC, deposit). Portal APIs enrich with actions/stats only—rules stay in the engine.

---

## FEATURES

- **ScanStation:** Multi-client capture, queue, Quick/Careful, property naming from `/docs`, session summary / intelligence, rescan integration, camera controls.
- **ReviewStation:** Filtering, batch dates, export history, keyboard shortcuts, portal deep-link.
- **Delivery viewer:** Offline-capable when `ARCHIVE_DATA` embedded; PDF search best-effort on HTTP.
- **portal_new:** 8-page IA (Overview, Properties, Compliance, Documents, Packs, Ask AI, Reports, Settings); split-panel property list + detail; compliance matrix; document card grid; placeholder packs builder; AI chat welcome screen; audit trail; settings sub-nav; `?client=` scoping.

---

## DEPENDENCIES

| Component | Purpose |
|-----------|---------|
| Python 3.x | All scripts |
| Tesseract, ImageMagick, OCRmyPDF | OCR pipeline |
| openpyxl | Excel export |
| pdfplumber | Export text/fields |
| pdfminer.six | `/ocr-text` |
| Flask, flask-cors | `server.py` |
| flask-login, anthropic, reportlab | `portal_new` |

`setup_check.bat` does not verify pdfplumber, flask-login, anthropic, or reportlab—install per `portal_new/requirements.txt`.

---

## ENVIRONMENT VARIABLES

| Variable | Used by | If missing |
|----------|---------|------------|
| **`ANTHROPIC_API_KEY`** | `ai_prefill.py` (subprocess from watcher), `portal_new` POST `/api/chat`; load from **`.env`** at deploy root (not committed) | No AI classification/extraction; chat returns error. Pipeline still creates docs with manual review. |
| **`PORTAL_SECRET_KEY`** | Flask session signing in `portal_new` | Falls back to dev default in code—insecure for production; set explicitly when deploying. |

**Optional:** `MORPHIQ_*` / client name in front-end boot scripts—convenience for chat scope, not secrets.

---

## FAILURE MODES

| Component down | Effect |
|-----------------|--------|
| **Watcher** | Raw images accumulate; no new PDFs or AI prefill; ReviewStation sees no new docs. |
| **server.py (8765)** | ScanStation/ReviewStation broken (no `/docs`, `/pdf`, `/review`); portal PDFs and review sync fail; export cannot complete. |
| **portal_new (5000)** | Web UI and `portal.db` API unavailable; pipeline and ReviewStation still work on disk; exports can still build files. |
| **Claude (API key / network)** | No prefill; portal chat fails; manual typing in ReviewStation still works. |
| **Tesseract / ImageMagick** | OCR fails; docs may stay in Failed or error paths per watcher logic. |
| **portal.db corrupt/missing** | Portal errors; recreate from migrations + `sync_to_portal.py` from `Clients/`. |
| **Single DOC folder deleted** | Next sync removes stale portal rows; ReviewStation truth is filesystem. |

---

## TEST STATUS

- **Bulk import stress test** (`bulk_import.py` at deploy root, `BULK_IMPORT_SPEC.md`): Client A done; **Client B (Oakwood, 100 docs)** and **Client C (Riverside, 150 docs)** synced to portal; OCR complete; **AI prefill skipped** (watcher ran from stale path); all docs **Unknown/New**. **D and E not started.** Script maps A–E to fixed image slices (A skipped if passed), writes `.bulk_import.json`, `--cleanup` removes the five fictional client trees. Do not run `sync_to_portal.py` until a batch finishes.
- **Real-document E2E:** 10-doc mixed-type test (tenancy, gas, EICR, EPC, deposit) through Scan → Review → Export → portal—**not** closed as a completed test in this doc.
- **Regression:** Periodic `setup_check.bat`; portal exercised manually via `Start_System_v2.bat` during development—no automated CI suite documented here.

**Planned test client: "Harlow & Essex Lettings"** — fictional agency, 6 properties, 27 documents. Canonical dataset for full portal E2E verification. **Status: 4-session execution plan defined; Sessions 1–4 pending.**

| Property | Address | Scenario |
|----------|---------|----------|
| 1 | 4 Birchwood Close, Harlow, CM17 0PQ | Fully compliant — all 6 doc types verified, all certs valid |
| 2 | 12 Rosebank Avenue, Epping, CM16 5TH | All certs expiring within 60 days, all verified |
| 3 | 7 Thornfield Road, Harlow, CM20 1RQ | All certs expired, all verified |
| 4 | 23 Linnet Drive, Hoddesdon, EN11 8GF | Mixed: verified gas, AI prefilled EICR, expired EPC, missing deposit |
| 5 | 9 Coppice Lane, Bishops Stortford, CM23 2JP | Sparse: verified gas only, AI prefilled AST, EICR/EPC/DEP missing |
| 6 | 31 Mallard Way, Epping, CM16 7BN | AI prefill stress: all 6 doc types present, all AI prefilled, none verified |

Session plan:
- **Session 1** — Fix portal wiring (compliance strip, cert pills, alert banner, doc cards, urgency grouping). Confirm `renderDetail` fix works against real data.
- **Session 2** — Run `generate_test_documents.py` (27 JPEGs → `raw/`), process through watcher → OCR → AI prefill.
- **Session 3** — Run `set_test_verification_states.py` to set correct verification states per scenario. Run `sync_to_portal.py`.
- **Session 4** — Full 8-page portal verification against all 6 test properties. Fix remaining issues. Update PROJECT_BRAIN.md.

---

## DECISIONS LOCKED IN

1. MVP-first; letting/property focus; human verification; per-doc pricing; deliverable = Excel + folders + viewer (+ portal for demos).
2. Capture path: Camo/phone then DSLR acceptable for MVP.
3. Deploy root is **Desktop\MorphIQ\Product** (full path `C:\Users\user\OneDrive - University of East London\Desktop\MorphIQ\Product`). The legacy ScanSystem_v2 root on `C:\` is stale and abandoned. Batch/scripts use `%~dp0` or script-dir resolution—no hardcoded deploy root in committed `.bat` files.
4. **GitHub:** private repo at the deploy root (`Desktop\MorphIQ\Product`). Old clone at `Documents\GitHub\MorphIQ` is abandoned.
5. **Secrets:** `ANTHROPIC_API_KEY` (and related) loaded from `.env` only—never hardcoded in committed files.
6. AI doc-type matching **contains**-based, not exact string equality (see `ai_prefill.py`).
7. **Portal UX:** **Property-first** archive (properties, not flat document list) + **global document search**; not folder-first navigation. (Supersedes earlier “search-first table” wording.)
8. **portal.db** is SQLite at deploy root; no PostgreSQL.
9. **sync_to_portal.py** is the only bridge from `Clients/` JSON to `portal.db`; automatic on `/review` and `/export`; CLI for maintenance.
10. **PDF access:** ScanStation `/pdf/<client>/<doc_id>` serves capture/review; portal stores paths in DB and exposes **document viewer** streaming via `GET /api/documents/.../pdf` (same files on disk) + PDF.js—not iframe zoom to 8765 for that tab.
11. **Session Intelligence** panel is **browser-only**; no watcher changes for it.
12. **Exports / offline:** Delivery handoff still **`viewer.html` in package**; portal login required for web UI—not a standalone offline PDF app.
13. **Client scoping** via `?client=` (admins); managers locked to `client_id`.
14. **Client picker** when no client (admins); managers skip picker.
15. **Compliance rules** live in `compliance_engine.py`; APIs may enrich, not duplicate rules.
16. **Authentication** required for portal pages/APIs (Flask-Login).
17. **Sync after review** is mandatory path for portal freshness (`sync_single_doc`).
18. **Portal IA v2:** 8-page structure (Overview, Properties, Compliance, Documents, Packs, Ask AI, Reports, Settings). Properties uses split-panel (not table). Packs is new feature (placeholder UI, backend not yet built). Reports combines templates + history + audit trail. Old routes (/dashboard, /archive, /activity, /ai-chat) redirect to new equivalents.
19. **Packs** are client-scoped, user-created document collections stored in portal.db. "Add to Pack" modal is global (base.html). Exports are ZIP (individual PDFs) or PDF bundle (ReportLab cover + merged PDFs). Pack documents reference documents table by ID — removing from pack does not delete the document.
20. **Documents API** supports server-side search across title, property address, and field values; type and status filtering; sort by recent/property/type. Frontend debounces search at 300ms.
21. **Properties API** returns per-property compliance badges and overall status in a single batched query — does not call compliance_engine per property.
22. All pipeline scripts (`auto_ocr_watch.py`, `ai_prefill.py`, `export_client.py`) use `Path(__file__).resolve().parent` for BASE path resolution. No hardcoded deploy root in any committed Python file. `server.py` and `sync_to_portal.py` already used script-relative resolution. The legacy `C:\ScanSystem_v2` path is fully removed from all code.
23. Required fields per document type are defined in ai_prefill.py and used for completeness scoring. property_address is mandatory for verification across all document types — ReviewStation enforces this as a gate.
24. Multi-page documents use a group_id system: ScanStation writes grouped `.meta.json` files with shared group_id + `.group_complete` marker. Watcher waits for `.group_complete` before processing, then combines all pages into a single multi-page PDF in one DOC folder. ReviewStation will support post-capture merge and split.
25. Watcher syncs to portal.db exclusively via `sync_single_doc` after AI prefill — no direct portal.db inserts in `process_file()` or `process_group()`. sync_to_portal.py remains the sole bridge between filesystem review.json and portal.db.
26. **Properties page uses split-panel layout** (320px left fixed, flex-1 right) as the canonical design. Left panel groups properties by urgency status with section labels. Right panel has 3 tabs: Documents, Compliance timeline, Property info. This is the confirmed IA and will not be restructured.
27. **Test client "Harlow & Essex Lettings"** is the canonical test dataset for full portal E2E verification. 6 properties covering all compliance scenarios. 27 documents. Generated via `generate_test_documents.py` (JPEGs + `.meta.json`). Status set via `set_test_verification_states.py` after pipeline processing.
28. **Synthetic test documents are JPEGs (not PDFs)** — the watcher pipeline expects image files in `raw/`. A4 at 300dpi (2480×3508px), white background, black text, large font for Tesseract reliability.
29. **Git commit discipline:** commit after every confirmed working session before starting the next. Message format: `fix: [what was fixed]` or `feat: [what was added]`.
30. **python-dotenv** to be installed to resolve Flask `.env` warning — non-blocking but should be resolved before Hetzner deployment.

---

## OPEN QUESTIONS

- Long-term: keep bundling **viewer.html** in every delivery for offline handoff, or rely on portal-only demos?
- Add **additional compliance types** (e.g. fire safety, Right to Rent) before first paid client?
- **Inline editing** of verification status/fields in portal vs ReviewStation-only—ever needed?

---

## ACTION ITEMS

1. **SESSION 1 — Fix portal wiring:** diagnose why compliance strip shows "Not on file" when docs exist. Fix compliance strip, cert pills, alert banner, document cards, and urgency grouping to read real data from portal.db via compliance_engine and `/api/properties/<id>`. Confirm `renderDetail(data.property)` fix works. Commit after confirmed working.

2. **SESSION 2 — Run `generate_test_documents.py`:** creates 27 JPEGs + `.meta.json` files for Harlow & Essex Lettings across 6 properties in `Clients/Harlow & Essex Lettings/raw/`. Stop watcher first. Requires Pillow installed. Commit after confirmed working.

3. **SESSION 3 — Run pipeline + `set_test_verification_states.py`:** process JPEGs through watcher → OCR → AI prefill, then set correct verification status per document per test scenario. Run `sync_to_portal.py` after. Commit after confirmed working.

4. **SESSION 4 — Full 8-page portal verification** against all 6 test properties. Fix any remaining issues found. Update PROJECT_BRAIN.md.

5. Validate **double-write fix** with a fresh real document scan — confirm document appears in portal without manual `sync_to_portal.py` run.

6. Run `simulate_multipage.py` to test **multi-page group processing** end-to-end.

7. Verify **portal authentication** works locally (login, logout, protected route redirects).

8. Connect **Report template "Generate" buttons** to actual report generation endpoints.

9. Wire **"Add to Pack"** on Ask AI result cards (requires AI to return structured document IDs).

10. **Deposit Protection + Inventory templates** missing from `Templates/` — build when real documents of these types are scanned.

11. **Hetzner VPS deployment** — portal only, Ubuntu 24.04, Gunicorn + Nginx, HTTPS, synthetic demo data in portal.db. Not started.

12. **Install python-dotenv:** `pip install python-dotenv --break-system-packages`

---

## CHANGE LOG

| Date | Summary |
|------|---------|
| 2026-04-03 | Properties page full redesign: split-panel control room layout, 4-block compliance strip, cert pills with real status colours, urgency grouping (Needs immediate action / At risk / Compliant), contextual alert banners, document cards with trust badges and 3-column extracted field grids, 3-tab right panel (Documents / Compliance timeline / Property info). Portal wiring bug identified: compliance strip shows "Not on file" regardless of actual DB state — `renderDetail(data)` → `renderDetail(data.property)` fix applied, pending verification. Session-based client persistence added to `get_current_client()` (Flask session) — fixes `&` in client name breaking `?client=` URL param. `generate_test_documents.py` (Pillow JPEG generator), `set_test_verification_states.py` (direct DB writer), `admin_delete_client.py` created. 4-session test plan defined for "Harlow & Essex Lettings" fictional test client (6 properties, 27 docs, all compliance scenarios). PROJECT_BRAIN.md updated. **Claude.ai + Claude Code** |
| 2026-03-30 | Portal `/properties`: compliance summary strip (per-cert dots + counts from API, click to filter doc cards / All); list auto-selects first visible property on load and when filter/search changes. **Cursor** |
| 2026-03-26 | Watcher double-write fix: removed direct portal.db inserts from process_file() and process_group() in auto_ocr_watch.py. Both now call sync_single_doc from sync_to_portal.py after AI prefill completes. Documents appear in portal with correct classification immediately. ReviewStation merge/split built: POST /merge/<client> combines 2+ DOC records into one multi-page PDF (pypdf merge, first DOC retained, cleanup, re-prefill, portal sync). POST /split/<client>/<doc_id> extracts each page into separate DOC records. UI: 'Merge Selected' button on multi-select, 'Split Pages' button on multi-page docs. simulate_multipage.py utility script added to project root for testing multi-page watcher processing without a camera. **Claude.ai + Cursor** |
| 2026-03-25 | ScanStation multi-page capture: 'Add Page' button + P shortcut, group_id tracking in .meta.json, .group_complete marker file, session queue indented page display, multi-page indicator bar, Finish Document / Escape to close groups. Single-page capture unchanged. Watcher `process_group()` built: detects .group_complete markers, collects grouped images, merges preprocessed pages into multi-page TIFF → OCRmyPDF → single searchable PDF in one DOC folder, AI prefill on combined PDF, portal.db insert, cleanup of meta + marker files. Single-page groups delegate to `process_file()`. ReviewStation merge/split not yet built. **Claude.ai + Cursor** |
| 2026-03-25 | AI prefill quality assessment: completeness_score, missing_fields, needs_attention written to review.json per document type. ReviewStation triage: amber warning dots, auto-sort attention-needed first, field highlighting for missing fields, verification gate blocking empty property_address. Portal: Unassigned property info banner and subtitle. **Claude.ai + Cursor** |
| 2026-03-25 | Infrastructure fix: replaced hardcoded `C:\ScanSystem_v2` paths in `auto_ocr_watch.py` (3 refs: BASE, portal.db path, subprocess cwd), `ai_prefill.py` (1 ref: BASE), `export_client.py` (1 ref: BASE) with `Path(__file__).resolve().parent`. Pipeline now works from any deploy location. Confirmed Ligant Agency 11-doc scan → OCR → AI prefill → portal sync working end-to-end from Desktop\MorphIQ\Product. **Claude.ai + Cursor** |
| 2026-03-24 | Bug fixes post-wiring: Add-to-Pack modal always visible (CSS `display:flex` overrode `hidden` attr — fixed with `[hidden]{display:none}`); Overview JS SyntaxError from duplicate `const health` in `load()` blocked all data render — renamed second to `filteredHealth`, fixed filter to use `h.type`. Properties badges and Packs API confirmed correct (no code change). **Cursor** |
| 2026-03-24 | Portal wiring phase — Properties API enriched (per-property compliance badges, overall_status, doc_count, tenant_name via batched query). Documents API wired (server-side ?q/?type/?status/?sort search with debounced frontend). Packs feature built end-to-end: packs + pack_documents tables, 10 CRUD API endpoints, Add to Pack modal in base.html, ZIP + PDF bundle export. **Cursor** |
| 2026-03-24 | Portal: visual polish pass — Overview hero layout (score ring + status cards side-by-side, cert coverage bars, expiry timeline with colour-coded buckets, activity + packs side-by-side), Compliance matrix cleanup (removed redundant subtitles, styled risk banner, alternating rows), Settings sub-nav fixed (horizontal tabs or compact sidebar replacing empty panel), Reports restructured (template card grid + stacked sections), document cards standardised (2-col key fields, truncated values, icon action buttons, status pills), property list cert badges resized to pills, pack builder numbered rows + drag handles + sticky export bar. **Cursor** |
| 2026-03-24 | Portal: IA restructure to 8 pages — Overview (score ring + expiry timeline), Properties (split-panel + cert badges), Compliance (risk banner + matrix), Documents (search + card grid), Packs (split-panel builder, placeholder), Ask AI (welcome + suggestions + chat), Reports (templates + audit trail), Settings (team + notifications + permissions). Old routes redirect. Sidebar updated. **Cursor** |
| 2026-03-23 | Portal: `/dashboard` full-viewport layout (`portal-main--stack`); compliance hero + **`GET /api/dashboard-stats`** (shared snapshot with `/api/compliance`, other-doc coverage, lists up to 500 rows); `compliance_engine` other-present helper. **Cursor** |
| 2026-03-22 | Ops: BitLocker; `.env`; `setup_check.bat`; `rerun_prefill.py`; GitHub. Portal: `/ai-chat`; `/dashboard` & `/archive`; overview (attention-by-property, coverage). **Cursor** |
| 2026-03-21 | `setup_check.bat`: `%~dp0` for `auto_ocr_watch.py` + `Templates\tenancy_agreement.json`; stale `C:\` root removed; fixed parenthesized `if`/`echo` pitfalls (summary line, ImageMagick URL `^#`). **Cursor** |
| 2026-03-21 | Deploy root set to OneDrive `...\MorphIQ\Product`; bulk test B/C synced (OCR ok, AI prefill skipped, Unknown\|New). **Cursor** |
| 2026-03-21 | Portal: same-tab archive→document; viewer close (×/Escape) to `#archive`; same-origin PDF + PDF.js fit-page; AI FAB icon-only + partial; no Archive footer brand; `/document/by-id` + client/source match; `imported_at` SQL fix. **`bulk_import.py`:** stdlib stress feeder (`--source`/`--client`, `.bulk_import.json`, `--cleanup`). **Cursor** |
| 2026-03-20 | Portal: luminous archive shell, compliance History tab, snooze 1–730, `tojson` fixes, dead-code cleanup. |
| 2026-03-16 | Logo assets; resolve/snooze UX; dashboard Overview/Archive; storage bar removed; FE compliance dedup. |
| 2026-03-15 | Portal Sessions 1–5: auth, search, upload, chat, reports, settings, activity, sidebar nav, compliance actions. |
| 2026-03-13 | Open Portal buttons; client picker; auto-sync on review; enriched property/compliance APIs. |
| 2026-03-10 | Property-first portal; compliance dashboard v1; `imported_at` SQL fixes in property paths. |
| 2026-03-09 | Start script includes portal_new; export opens portal URL; PDF via API; AI unknown doc type at capture. |
| 2026-03-08 | portal_new replaces legacy portal for exports; sync_to_portal staleness cleanup. |
| 2026-03-07 | portal_new SQL schema alignment (`key`/`label`, `address`); ai_prefill six types + fuzzy match. |
| 2026-02-23 | Rescan workflow v2; User_Guide; Viewer PDF.js; ScanStation `.meta.json` + session summary; initial pipeline/docs baseline (Filip / Claude). |

---

*End of PROJECT_BRAIN.md*
