# PROJECT BRAIN — ScanStation Document Archiving System

> **Last updated:** 2026-03-21  
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

- **Pipeline:** ImageMagick → OCRmyPDF + Tesseract → searchable PDF; watcher polls `Clients/*/raw/` every 2s, creates `Batches/date/DOC-XXXXX`, runs AI prefill after each new doc, supports `.meta.json` and `.reprocess` in place.
- **ScanStation** (`scan_station.html`): Capture, session queue, rescan flow, Export/Open Portal, camera settings (MediaStream), Live Session Intelligence panel (client-side counts only).
- **ReviewStation** (`review_station.html`): Dashboard, review with PDF/OCR text, status workflow, rescan reasons, Enter-to-save fields without advancing, Open Portal, auto-sync to portal on save.
- **API** (`server.py`, `http://127.0.0.1:8765`): Clients, docs, review, PDF, export, delivery, rescan, OCR text; CORS for `file://`; POST `/review` calls `sync_single_doc`; POST `/export` runs export + full portal re-sync.
- **Export** (`export_client.py`): Verified docs → delivery folder, Excel, `archive_data.json`, embedded `viewer.html`.
- **Viewer** (`viewer.html`): Delivery archive browser; PDF.js + search when served over HTTP.
- **AI prefill** (`ai_prefill.py`): Claude classification when type unknown; six doc types with dedicated prompts; fuzzy “contains” matching; `ANTHROPIC_API_KEY` passed from watcher env.
- **Portal** (`portal_new/`, `http://127.0.0.1:5000`): Flask-Login; admin vs manager (`client_id` scoping); property-first archive + Overview; client picker; `/property`, `/compliance`, `/settings`, `/activity`, `/ai-chat`; **Archive** table opens documents **in the same tab** (Ctrl/Cmd/Shift+click for a new tab); **document viewer** streams PDF via `GET /api/documents/.../pdf` + PDF.js (fit page in panel); **×** / Escape returns to portfolio `#archive`; **AI** chat FAB is **icon-only** (shared SVG partial: document + bolt); ScanStation `/pdf/` for capture/review; compliance engine, reports, search, upload, chat, activity; dates via `COALESCE(batch_date, scanned_at, reviewed_at)` not `imported_at`.
- **Sync** (`sync_to_portal.py`): CLI + automatic single-doc and export-time full sync; prunes stale rows; `cleanup_empty_properties`.
- **Ops:** `Start_System_v2.bat` starts watcher + API + portal; `User_Guide/` present; `setup_check.bat` validates core deps (not pdfplumber / flask-login / anthropic); `bulk_import.py` (stdlib-only) stress-feeds numbered `.jpg` into `Clients/*/raw/` for B–E runs.

### Not done / product gaps

- Deposit Protection + Inventory **templates** not in `Templates/` (export/general still use placeholders where applicable).
- Formspree / hosting / phone / GDPR as in BUSINESS.
- Operator “portal quickstart” doc not written.
- Archive **scoped export** (filter by status/type from UI) still TODO; dashboard export is compliance/property reports as implemented.

### Known issues

- **WinError 2** in `pipeline.log` during OCR—usually non-fatal; PDF still produced (often Ghostscript/jbig2 toolchain). **Ghostscript** optional on PATH; OCRmyPDF may warn without it.

---

## SYSTEM ARCHITECTURE

**Deploy root:** `C:\Users\user\OneDrive - University of East London\Desktop\MorphIQ\Product` (`setup_check.bat` uses `%~dp0` for file checks, same idea as `Start_System_v2.bat`).

**Core layout:**

```
C:\Users\user\OneDrive - University of East London\Desktop\MorphIQ\Product\
├── auto_ocr_watch.py, server.py, export_client.py, sync_to_portal.py, ai_prefill.py
├── scan_station.html, review_station.html, viewer.html
├── Start_System_v2.bat, Stop_System.bat, Stop_Watcher.bat, setup_check.bat
├── bulk_import.py       # optional synthetic load into Clients/*/raw/
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

**Pages:** `GET /`, `/compliance`, `/property/<id>`, `/settings`, `/activity`, `/ai-chat`; `GET/POST /login`, `GET /logout`.

**JSON API (representative):** `GET /api/clients`, `DELETE /api/clients/<id>`, `GET /api/properties[?client=]`, `GET /api/properties/<id>`, `POST /api/properties/<id>/download-pack`, `GET /api/properties/<id>/report`, `GET /api/documents`, `GET /api/documents/<source_doc_id>`, `GET /api/documents/by-id/<id>`, `GET /api/documents/by-id/<id>/pdf`, `GET /api/documents/by-source/<source_doc_id>/pdf`, `POST /api/documents/upload`, `GET /api/compliance`, `POST /api/compliance/actions/resolve`, `POST /api/compliance/actions/snooze`, `DELETE /api/compliance/actions/resolved` (admin), `GET /api/compliance/report`, `POST /api/chat`, `GET /api/activity`, `GET /api/settings/users`, `POST /api/settings/notifications` (placeholder).

**DB:** `portal.db` — clients, document_types (`key`/`label`), properties (`address`), documents, document_fields, tenants, compliance_records, `users`, `compliance_actions`, `activity_log` (see `app.py` migrations).

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
- **portal_new:** Overview + Archive (doc → **same-tab** viewer); property drawer; compliance; search; upload; reports; chat; settings; activity; `?client=` scoping.

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
| **`ANTHROPIC_API_KEY`** | `ai_prefill.py` (subprocess from watcher), `portal_new` POST `/api/chat` | No AI classification/extraction; chat returns error. Pipeline still creates docs with manual review. |
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

- **Bulk import stress test** (`bulk_import.py` at deploy root, `BULK_IMPORT_SPEC.md`): Client A done; **Client B (Oakwood Lettings, 100 docs)** and **Client C (Riverside Property Management, 150 docs)** synced to portal; OCR complete; **AI prefill skipped** (watcher had been started from the stale `C:\` root); all docs **Unknown \| New**. D–E pending. Script maps A–E to fixed image slices (A skipped if passed), writes `.bulk_import.json`, `--cleanup` removes the five fictional client trees. Do not run `sync_to_portal.py` until a batch finishes.
- **Real-document E2E:** 10-doc mixed-type test (tenancy, gas, EICR, EPC, deposit) through Scan → Review → Export → portal called out in Action Items—**not** closed as a completed test in this doc.
- **Regression:** Periodic `setup_check.bat`; portal exercised manually via `Start_System_v2.bat` during development—no automated CI suite documented here.

---

## DECISIONS LOCKED IN

1. MVP-first; letting/property focus; human verification; per-doc pricing; deliverable = Excel + folders + viewer (+ portal for demos).
2. Capture path: Camo/phone then DSLR acceptable for MVP.
3. Deploy root is **Desktop\MorphIQ\Product** (OneDrive-synced; full path `C:\Users\user\OneDrive - University of East London\Desktop\MorphIQ\Product`). The prior default root on `C:\` (legacy ScanSystem folder) is stale—do not reference it in docs or batch files.
4. AI doc-type matching **contains**-based, not exact string equality (see `ai_prefill.py`).
5. **Portal UX:** **Property-first** archive (properties, not flat document list) + **global document search**; not folder-first navigation. (Supersedes earlier “search-first table” wording.)
6. **portal.db** is SQLite at deploy root; no PostgreSQL.
7. **sync_to_portal.py** is the only bridge from `Clients/` JSON to `portal.db`; automatic on `/review` and `/export`; CLI for maintenance.
8. **PDF access:** ScanStation `/pdf/<client>/<doc_id>` serves capture/review; portal stores paths in DB and exposes **document viewer** streaming via `GET /api/documents/.../pdf` (same files on disk) + PDF.js—not iframe zoom to 8765 for that tab.
9. **Session Intelligence** panel is **browser-only**; no watcher changes for it.
10. **Exports / offline:** Delivery handoff still **`viewer.html` in package**; portal login required for web UI—not a standalone offline PDF app.
11. **Client scoping** via `?client=` (admins); managers locked to `client_id`.
12. **Client picker** when no client (admins); managers skip picker.
13. **Compliance rules** live in `compliance_engine.py`; APIs may enrich, not duplicate rules.
14. **Authentication** required for portal pages/APIs (Flask-Login).
15. **Sync after review** is mandatory path for portal freshness (`sync_single_doc`).

---

## OPEN QUESTIONS

- Long-term: keep bundling **viewer.html** in every delivery for offline handoff, or rely on portal-only demos?
- Add **additional compliance types** (e.g. fire safety, Right to Rent) before first paid client?
- **Inline editing** of verification status/fields in portal vs ReviewStation-only—ever needed?

---

## ACTION ITEMS

1. Run **10-document E2E** (mixed types) through full pipeline and confirm portal (Overview, Archive, Property, Compliance).
2. Spot-check **AI extraction** quality across all six types on real scans.
3. **Compliance dedup** and **Needs Attention** counts vs `/api/compliance` on a real demo client.
4. Short **operator guide** for Overview vs Archive vs Compliance.
5. **Demo pack** + schedule first agency visits.

---

## CHANGE LOG

| Date | Summary |
|------|---------|
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
