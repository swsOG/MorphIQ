# PROJECT BRAIN — ScanStation Document Archiving System
> **Last updated:** 2026-02-23
> **Purpose:** Single source of truth for the current system. Read this before making changes.

---

## BUSINESS

**What:** Local document scanning and digital archiving service for letting agencies and landlords in the Harlow, Essex area.

**Value prop:** "Not just scanned — understood." Clients get searchable PDFs, verified key fields, organised folders, and a delivery spreadsheet. Human-verified, not just OCR output.

**Differentiator:** Per-document pricing with verified field extraction. Generic scanning companies charge per page with no intelligence layer.

**Target market:** Letting agencies managing 50–500+ properties in Harlow, expanding to Chelmsford, Bishop's Stortford, and London corridor.

**Business name:** Morph IQ (landing page built, not yet live)

---

## CURRENT STATE

### What's working:
- Full OCR pipeline: ImageMagick → OCRmyPDF + Tesseract → searchable PDF ✅
- **ScanStation** (scan_station.html): 3-column layout; camera preview, Client/Doc Type/Property; session queue from GET `/docs/<client>` (excludes "Sent to Rescan"); center preview (canvas/iframe PDF); Select Folder, Browse Files, Capture Document; Quick/Careful mode; property autocomplete and auto-naming "Property - DocType N"; Session progress and Session Summary (by doc type and property); Rescan Requests panel with per-doc cards (thumbnail via `/doc-image`, Rescan Now, rescan mode with Capture Replacement and Browse → `/rescan-replace`); pipeline status (GET `/health` every 5s); Export Verified (POST `/export`), Open Review Station; export success → open folder (POST `/open-folder`) and viewer in new tab ✅
- **ReviewStation** (review_station.html): View 1 client picker; View 2 dashboard (status cards New, Needs Review, Failed, Verified, Sent to rescan, All; batch date filter; doc table; Export section, Export History GET `/exports/<client>`); View 3 document review (PDF GET `/pdf`, fields panel, Reviewed by/Notes, Previous/Next, Verified/Needs Review/Failed, Request re-scan with reason modal → POST `/reprocess` with `{ reason }`); Show OCR Text (GET `/ocr-text`); 5s polling; keyboard 1/2/3 and ArrowLeft/ArrowRight ✅
- **API server** (server.py): http://127.0.0.1:8765; CORS `origins=["null"]`; all endpoints documented below ✅
- **Auto-watcher** (auto_ocr_watch.py): Polls each client `raw/` every 2s; skips `_*`; processes images → Batches/date/DOC-XXXXX; checks `.reprocess` triggers and reprocesses in place; supports `.meta.json` for doc_name, property_address, doc_type_template ✅
- **Export** (export_client.py): Verified docs only; Delivery_YYYY-MM-DD_HHMM; property → doc type folders; pdfplumber full text + Tenancy Agreement field extraction; merge with verified fields; archive_data.json; viewer.html with ARCHIVE_DATA embedded; instruction_sheet.pdf → Instructions.pdf if present; Excel index; POST `/export` or CLI ✅
- **Viewer** (viewer.html): Loads from `window.ARCHIVE_DATA` or fetch `archive_data.json`; properties sidebar; document list by category; Document tab (PDF.js when HTTP, else iframe; search highlight on PDF when server); Details tab (fields + full_text with search highlight); search panel with results and snippets; file:// banner for PDF highlight note ✅
- **Delivery serving:** GET `/delivery/<client>/<export_folder>/<path:filepath>` serves Exports folder ✅
- 5 document type templates in Templates/ ✅
- **Batch files:** Start_System_v2.bat (watcher + server minimised, open scan_station.html); Stop_System.bat (kill watcher + API); Stop_Watcher.bat (kill watcher only); setup_check.bat (Python, Tesseract, ImageMagick, ocrmypdf, openpyxl, C:\ScanSystem_v2, Templates, flask, flask-cors, pdfminer.six) ✅
- **User_Guide/** folder with README, 01_ScanStation, 02_ReviewStation, 03_Viewer ✅

### What's NOT done yet:
- Pricing not finalised; no paying clients; no business phone number
- Form submission (Formspree) not connected; landing page hosting not set up
- No GDPR registration or data processing agreements
- Deposit Protection Certificate and Inventory/Check-in Report templates not yet created
- No client outreach started
- setup_check.bat does not verify pdfplumber (required by export_client.py)

### Known issues:
- **[WinError 2]** in pipeline.log during OCR — non-fatal; PDF still generated. May relate to ghostscript/jbig2.

### CURRENT STATE SNAPSHOT — 2026-02-23
- After each successful scan, the watcher now calls `ai_prefill.py` for that DOC folder to try to fill in fields automatically.
- OCR and review.json creation still work the same as before; the AI step runs afterwards.
- AI prefill logs success, warnings, or errors into the existing client pipeline log so humans can see what happened.
- A crash when trying to move the original image back on errors has been fixed; the move now only runs if the source file actually exists.
- AI prefill now recognises any doc_type containing the word “Tenancy” (e.g. “Tenancy Agreement (AST)”) as a tenancy agreement and runs the correct field extraction.
- When inserting into portal.db, the watcher now looks up or creates the right client, property (by client + address), and document type rows instead of using hardcoded IDs, so source_doc_id remains unique per client.
- The watcher now passes the current environment (including `ANTHROPIC_API_KEY`) into the `ai_prefill.py` subprocess so Claude prefill works reliably.
- Next step: teach the AI prefill script how to handle more document types beyond tenancy agreements and monitor logs for any remaining watcher/db errors.

---

## SYSTEM ARCHITECTURE

### Root path: `C:\ScanSystem_v2`

All scripts and batch files use this path.

### Full folder structure (project files only):

```
C:\ScanSystem_v2\
├── auto_ocr_watch.py           # Watcher: raw/ polling + .reprocess triggers
├── server.py                   # Flask API (port 8765), CORS for file://
├── export_client.py            # Export: PDFs, Excel, archive_data, viewer embed
├── scan_station.html           # Capture app: 3 columns, rescan panel, session summary
├── review_station.html         # Review app: 3 views, rescan reason modal
├── viewer.html                 # Archive viewer: properties, docs, PDF+Details, search
├── Start_System_v2.bat         # Start watcher + server, open ScanStation
├── Stop_System.bat             # Stop watcher and API server
├── Stop_Watcher.bat            # Stop watcher only
├── setup_check.bat             # Validate Python, Tesseract, ImageMagick, ocrmypdf, openpyxl, flask, flask-cors, pdfminer.six, C:\ScanSystem_v2, Templates
├── SETUP_GUIDE.md              # New PC setup
├── User_Guide\
│   ├── README.md
│   ├── 01_ScanStation.md
│   ├── 02_ReviewStation.md
│   └── 03_Viewer.md
├── PROJECT_BRAIN.md            # ← THIS FILE
├── .cursorrules                # Cursor AI rules
├── __pycache__\                # Python bytecode (auto)
├── temp\                       # Watcher temp files (auto-cleaned)
├── Clients\
│   └── [ClientName]\
│       ├── raw\                # Images + _doctype.txt; optional .meta.json (deleted after read)
│       ├── Batches\YYYY-MM-DD\DOC-XXXXX\
│       │   ├── *.pdf, *.jpeg (or other image)
│       │   └── review.json
│       ├── Exports\Delivery_YYYY-MM-DD_HHMM\
│       │   ├── [PropertyFolder]\[DocTypeFolder]\*.pdf
│       │   ├── archive_data.json
│       │   ├── viewer.html     # Copy with ARCHIVE_DATA embedded
│       │   ├── [Client]_Document_Index_*.xlsx
│       │   └── Instructions.pdf (if instruction_sheet.pdf in root)
│       ├── rescan_queue.json   # [{ doc_id, requested_at, reason }]
│       └── Logs\pipeline.log
└── Templates\
    ├── tenancy_agreement.json
    ├── gas_safety_certificate.json
    ├── eicr.json
    ├── epc.json
    └── general_document.json
```

### API endpoints (server.py — http://127.0.0.1:8765)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Server alive. Returns `{ "status": "ok", "server": "ScanStation API", "port": 8765 }`. |
| GET | `/clients` | List client folder names. Returns `{ "clients": [...] }`. |
| POST | `/export` | Export verified docs. Body: `{ "client": "ClientName" }`. Returns `{ success, delivery_folder, document_count, spreadsheet, viewer_url }` or error. |
| POST | `/open-folder` | Open folder in file manager. Body: `{ "path": "C:\\...\\..." }`. Path must be under BASE. Returns `{ "success": true }` or error. |
| GET | `/delivery/<client_name>/<export_folder>/<path:filepath>` | Serve file from Clients/.../Exports/<export_folder>/<filepath>. 404 if filepath empty or not a file. |
| GET | `/stats/<client_name>` | Document counts. Returns `{ "client", "counts": { total, New, Verified, Needs Review, Failed, ... } }`. |
| GET | `/docs/<client_name>` | All docs with review data. Returns `{ "docs": [...], "counts": {...} }`. Each doc: doc_id, doc_name, doc_type, status, batch_date, scanned_at, reviewed_at, exported_at, folder_path, fields, review. |
| POST | `/review/<client_name>/<doc_id>` | Save review. Body: `{ status?, fields?, review? }`. Merges into existing review.json. Returns `{ "success": true }`. |
| GET | `/pdf/<client_name>/<doc_id>` | Serve PDF from DOC folder. |
| GET | `/raw-image/<client_name>/<filename>` | Serve raw image from Clients/<client>/raw. |
| GET | `/raw-list/<client_name>` | List raw image filenames. Returns `{ "files": [...] }`. |
| GET | `/doc-image/<client_name>/<doc_id>` | Serve raw image from DOC folder (first image found). For rescan thumbnail/preview. |
| GET | `/ocr-text/<client_name>/<doc_id>` | Extract text from PDF (pdfminer). Returns `{ "text", "error" }`. |
| POST | `/reprocess/<client_name>/<doc_id>` | Mark for rescan. Body: `{ "reason": "..." }`. Sets status "Sent to Rescan", review.notes, rescan_requested_at; appends to rescan_queue.json. Does NOT copy to raw. Returns `{ success, doc_id, message }`. |
| POST | `/rescan-replace/<client_name>/<doc_id>` | Replace scan. Form: `image` file. Saves to DOC folder (rescan.ext), deletes old image/PDF, updates review.json (Reprocessing, empty fields from template), writes `.reprocess` with new image filename. Returns `{ success, doc_id, message }`. |
| GET | `/exports/<client_name>` | List Delivery_* folders. Returns `{ "exports": [ { folder_name, date, document_count } ] }`. |
| GET | `/rescan-queue/<client_name>` | Enriched queue. Returns `{ "queue": [ { doc_id, doc_name, doc_type, reason, requested_at, has_image } ] }`. |

CORS: `origins=["null"]` for file:// pages.

### Doc type flow
1. ScanStation: user selects doc type → when saving to raw, writes template name (e.g. tenancy_agreement) to `raw/_doctype.txt`; optional `.meta.json` (doc_name, property_address, doc_type_template) is written alongside capture and deleted by watcher after read.
2. Watcher: for each new image, reads `_doctype.txt` (or from .meta.json if present); loads template from Templates/<name>.json; generates review.json with template fields and doc_type; if .meta.json had doc_name/property_address, pre-fills fields and stores doc_name.

### Document unit
Each DOC-XXXXX folder contains: one PDF, one raw image (any of .jpg, .jpeg, .png, .tiff, .tif, .bmp), and review.json. review.json includes: doc_id, doc_type, doc_type_template (display name from template), status, quality_score, files (pdf, raw_image), fields (key-value from template), review (reviewed_by, reviewed_at, exported_at, scanned_at, notes). Status may be "New", "Needs Review", "Failed", "Verified", "Sent to Rescan", "Reprocessing". Optional doc_name. rescan_requested_at, rescan_at when applicable.

### Processing pipeline (auto_ocr_watch.py)
1. Infinite loop: for each client dir in Clients/, ensure raw exists; for each file in raw/ not starting with "_", if extension in .jpg/.jpeg/.png/.tiff/.tif/.bmp, call process_file(); then call check_reprocess_triggers(client_name, client_dir); sleep 2s.
2. process_file: wait_until_stable(image_path); if .meta.json exists beside image, read and delete it (doc_type_template, doc_name, property_address → initial_fields); else get_doc_type_for_file (read _doctype.txt); load_template(); batch_folder = Batches/YYYY-MM-DD; doc_id = get_next_doc_id(); create doc_folder; preprocess_for_ocr (ImageMagick: strip, auto-orient, gray, density 300, trim, border 20, contrast-stretch 1%x1%, adaptive-sharpen) → temp PNG; ocr_to_pdf (ocrmypdf --image-dpi 300 --force-ocr --deskew --rotate-pages --tesseract-pagesegmode 4 -l eng); move image to doc_folder; write_review_json (status New, fields from template, scanned_at). On error: move image back to raw if possible, remove empty doc_folder.

### Reprocessing pipeline
1. check_reprocess_triggers(client_name, client_dir): for each date_folder in Batches/, for each doc_folder in date_folder, if .reprocess file exists: read image filename from .reprocess; if that image exists in doc_folder, run preprocess_for_ocr(image_path, temp_png), ocr_to_pdf(temp_png, pdf_path in same folder), update review.json (status New, files, review.scanned_at), delete temp_png and .reprocess, remove doc_id from rescan_queue.json. If image missing, delete .reprocess.

### Export pipeline (export_client.py)
1. collect_verified_docs(client_name): scan all Batches/date/DOC-*/review.json; keep only status "Verified"; return list of { data, doc_folder, date_folder_name, pdf_file }.
2. Create Exports/Delivery_YYYY-MM-DD_HHMM.
3. package_pdfs: for each doc, extract_pdf_text (pdfplumber), extract_fields_from_text (Tenancy Agreement regex patterns), merge_fields (verified overrides extracted); property_folder = sanitize(property_address or "Unsorted"); category = DOC_TYPE_FOLDERS[doc_type]; create property_dir/category; make_clean_filename from fields; copy PDF; mark_doc_exported (exported_at in review.json); build archive_docs list (doc_id, doc_name, doc_type, filename, pdf_path, fields, full_text, property_address).
4. build_spreadsheet: Excel with title, subtitle, headers (Doc ID, Document Type, Batch Date, File Location, all field keys, Reviewed By, Reviewed At, Exported At, Notes), data rows.
5. generate_archive_data: build properties → category → list of docs; write archive_data.json (client_name, generated_date, version, total_documents, properties).
6. copy_viewer_assets: read viewer.html, inject archive_data.json into window.ARCHIVE_DATA, write to delivery_dir/viewer.html; if instruction_sheet.pdf in BASE, copy to Instructions.pdf.
7. Return { success, delivery_folder, document_count, spreadsheet }. Server adds viewer_url.

### Rescan workflow
1. ReviewStation: user clicks "Request re-scan" → modal "Why does this need rescanning?" with options (Blurry / out of focus, Cropped / cut off, Wrong document, Too dark / too light, Other with text). Submit → POST `/reprocess/<client>/<doc_id>` with `{ reason }`. Server sets status "Sent to Rescan", review.notes "Rescan requested: {reason}", appends to rescan_queue.json; does NOT copy image to raw.
2. ScanStation: GET `/rescan-queue/<client>` returns queue with doc_name, doc_type, reason, has_image. Panel shows per-doc cards: thumbnail (GET `/doc-image` or placeholder), doc type, name, doc_id, reason, button "Rescan Now".
3. Operator clicks Rescan Now: enterRescanMode(item); center shows old image from `/doc-image`; banner "RESCANNING DOC-XXXXX — …"; Capture button becomes "Capture Replacement" (amber). Space or button → capture from video, POST to `/rescan-replace` with FormData image; or Browse Files → same POST with selected file. On success, exitRescanMode(), refresh queue. Escape cancels rescan mode.
4. Server rescan-replace: save new image to DOC folder, delete old image and PDF, set review status "Reprocessing", empty fields from template, write .reprocess with new image filename.
5. Watcher: check_reprocess_triggers finds .reprocess, runs ImageMagick + OCR in same DOC folder, sets status "New", removes .reprocess and removes doc from rescan_queue.json.

### Dependencies

| Dependency | Purpose | Used in |
|------------|---------|---------|
| Python 3.x (pip) | Scripts | All .py |
| Tesseract OCR | OCR (via OCRmyPDF) | auto_ocr_watch |
| ImageMagick 7.1.2-Q16 | Preprocess | auto_ocr_watch (MAGICK path hardcoded) |
| OCRmyPDF | Searchable PDF | auto_ocr_watch |
| openpyxl | Excel export | export_client |
| Flask | API server | server |
| flask-cors | CORS for file:// | server |
| pdfminer.six | OCR text extraction | server (ocr-text), review_station |
| pdfplumber | PDF text + field extraction | export_client |
| Camo (optional) | Phone as webcam | — |

setup_check.bat does not check pdfplumber.

### Supported image formats
.jpg, .jpeg, .png, .tiff, .tif, .bmp

---

## SCANSTATION FEATURES

**Layout:** Header (logo, Camera select, Client select, Doc Type select, Property input with datalist), stats bar (captured count, session time, last doc), three columns: Left (camera preview 4:3, Session Queue with section count; queue items show name, docId, createdAt; click to preview); Center (empty state or preview — canvas for raw/session images, iframe for PDF from `/pdf` with #toolbar=0&navpanes=0&view=Fit; rescan banner when in rescan mode; quality overlay elements exist but quality badge/score tag IDs are not in HTML — flash classes applied to centerView); Action bar (Select Folder, Browse Files, Capture Document — or in preview mode naming input, Retake, Confirm); Right (Session progress: current/target input, progress bar, ETA; Session Summary: by doc type and by property; Rescan Requests: cards with thumbnail, doc type, name, doc_id, reason, Rescan Now). Footer: mode label, pipeline status (health every 5s), Export Verified, Open Review Station.

**Property naming and auto-numbering:** Property input has datalist from GET `/docs/<client>` (300ms debounce); sessionPropertyDocTypeCount tracks "property|docType" → count; getNextDocName() returns "Property - DocType N"; persistPropertyForClient/restorePropertyForClient use sessionStorage key scanstation_property_<client>. When saving to raw (saveFileToClient), writes _doctype.txt and optional .meta.json (doc_name, property_address, doc_type_template); watcher reads .meta.json and writes doc_name and property_address into review.json.

**Session summary:** updateSessionSummary() builds byType and byPropertyThenType from sessionDocs; renders types and property breakdown; session-summary-empty / session-summary-list.

**Rescan panel:** updateRetakeQueue() fetches GET `/rescan-queue/<client>`; renders queue as rescan-card items: thumbnail (img src `/doc-image/` or placeholder div), rescan-card-doctype, rescan-card-name, rescan-card-id, rescan-card-reason, button Rescan Now. Click Rescan Now → enterRescanMode(item); center shows old image via `/doc-image`, banner visible, Capture → "Capture Replacement" (btn-rescan-capture), footer "Rescan mode — Capture replacement or press Esc to cancel". captureRescanReplace(blob) POSTs to `/rescan-replace`; on success exitRescanMode(). Browse in rescan mode sends selected file to same endpoint. Escape → exitRescanMode().

**Quality:** analyzeImage(blob) returns brightness, contrast, sharpness, alignment, overall; qualityClassFromScore (good ≥80, ok ≥55, else bad); applyQualityToUI sets centerView flash-good/ok/bad, and tries to set qualityBadge, qualityIcon, qualityText, qualityScoreTag, mSharp/mBright/mContrast/mAlign — these IDs are not in the HTML so only flash on center works. No visible quality dashboard cards (updateDashboardCounts is no-op).

**Quick/Careful modes:** captureMode "quick" | "careful"; Quick → capture saves immediately with getNextDocName() and incrementCountForCurrentPropertyDocType(); Careful → showDocPreview(doc, "preview"), enterNamingMode() (name input, Retake, Confirm).

**Keyboard shortcuts (keydown, when not in rescan mode):** Escape (in nameInput: confirmCurrentName(true)); Enter (in nameInput: confirmCurrentName(false)); Space or Enter: captureImage(); B: browseFile(); R: if pendingCapture discardPendingCapture(); C: if viewMode !== "camera" exitPreviewToCamera(); Tab (viewMode preview && pendingCapture: focus nameInput). In rescan mode: Escape → exitRescanMode().

**API calls:** GET /clients (loadClientsFromApi), GET /docs/<client> (reloadClientFromRaw, fetchPropertySuggestions), GET /health (checkServer every 5s), GET /rescan-queue/<client> (updateRetakeQueue), GET /doc-image/ (rescan thumbnail and enterRescanMode image), GET /pdf/ (showDocPreview for queue doc with hasPdf), GET /raw-image/ (showDocPreview for doc.rawName), POST /rescan-replace/ (captureRescanReplace), POST /export (exportClient), POST /open-folder (after export). saveFileToClient uses File System Access API (no server call). rescanPollTimer setInterval updateRetakeQueue 10000.

---

## REVIEWSTATION FEATURES

**Views:** 1) Client picker — GET /clients, grid of client cards, click → selectClient(name), showView(2). 2) Dashboard — header with client name, Back; status cards (New, Needs Review, Failed, Verified, Sent to rescan, All) with counts; batch date filter dropdown; "Review All New" button; doc table (Doc ID, Doc Type, Timeline Scan/Review/Export, Status); Export section (message, Export Client Package, Export History from GET /exports/<client>). 3) Document review — Back, client name, doc id, status badge, doc type, counter; left panel: fields from review.json (editable), Reviewer section (Reviewed by, Notes); nav: Previous, Next; buttons Verified, Needs Review, Failed, Request re-scan; right: PDF iframe (GET /pdf with #toolbar=0&navpanes=0&view=FitH), "Show OCR Text" (GET /ocr-text).

**Status types:** New, Needs Review, Failed, Verified, Sent to Rescan (from rescan_queue; count from GET /rescan-queue). setStatusFilter(status) filters table; statusFilter can be "__rescan__" for Sent to rescan.

**Rescan request with reason:** reprocessDoc() opens modal #rescanModal with form #rescanReasonForm: radio options "Blurry / out of focus", "Cropped / cut off", "Wrong document", "Too dark / too light", "Other" (shows #rescanReasonOther text input). Cancel → closeRescanModal(); Submit → getRescanReasonValue(), closeRescanModal(), POST /reprocess with body JSON.stringify({ reason }), then loadDocs(), showView(2).

**Export:** exportClientPackage() POST /export with { client }; on success prompts "Open the delivery folder?", POST /open-folder, window.open(viewer_url). Export History from GET /exports/<client> (folder_name, date, document_count).

**Keyboard (viewReview active, not in input/textarea):** key "1" → saveAndAdvance("Verified"); "2" → saveAndAdvance("Needs Review"); "3" → saveAndAdvance("Failed"); ArrowLeft → prevDoc(); ArrowRight → nextDoc().

**API calls:** GET /clients, GET /docs/<client>, GET /rescan-queue/<client> (in loadDocs to set rescanDocIds and counts["Sent to Rescan"]), GET /exports/<client>, GET /pdf/<client>/<doc_id>, GET /ocr-text/<client>/<doc_id>, POST /reprocess/<client>/<doc_id>, POST /review/<client>/<doc_id>, POST /export, POST /open-folder. Polling: setInterval pollDocs 5000 when dashboard or review view active.

---

## VIEWER FEATURES

**Data loading:** loadArchive() checks window.ARCHIVE_DATA; if set (injected by export), uses it; else fetch('archive_data.json'). If both fail, replaces body with error message. init() sets clientName, archiveDate, builds allDocs from archiveData.properties (prop → category → docs), shows total count, renderFolders(). If protocol === 'file:', viewerFileNotice is shown (banner about opening from server for PDF search highlighting).

**Tabs:** Document tab (preview container with PDF or "Loading PDF…") and Details tab (fields + full text). showPreview(doc) builds preview container: if pdfSrc and pdfjsLib, renderPdfWithHighlight(pdfPath, wrap, getSearchQuery()); else iframe. Tab buttons data-tab="document" and data-tab="details"; switch shows/hides preview container or details panel.

**Search:** handleSearch() on input, 250ms debounce; if query length < 2, hide search panel and clear highlight; else set _searchHighlightQuery, performSearch(q), applyPdfHighlightToDocument(q). performSearch: filter allDocs by doc_name, fields, full_text; score and sort; show search panel with sr-list items (doc name, property › category, snippet with hl()); click result → selectDocById(doc_id). Details tab shows full_text with highlight via _searchHighlightQuery and hl() (sr-hl class). Document tab: applyPdfHighlightToDocument adds/removes pdf-search-highlight on text layer spans.

**Offline vs online:** When opened from file://, ARCHIVE_DATA is embedded so no fetch; PDFs are loaded via relative path in iframe or getDocument(pdfPath) (may fail for file://). When PDF.js fails, fallback iframe and notice "Open from the server URL after export for PDF search highlighting." or "Connect to internet for PDF search highlighting." When opened from HTTP (e.g. /delivery/.../viewer.html), fetch(pdfUrl) for PDF and PDF.js renders with text layer; search term highlighted on PDF.

**PDF.js:** Script 3.11.174 from CDN; workerSrc set. renderPdfWithHighlight: getDocument (from fetch arrayBuffer when HTTP, or getDocument(pdfPath) when file); render page 1 only; canvas + text layer (spans from getTextContent().items); applyPdfHighlightToDocument(getSearchQuery()) toggles .pdf-search-highlight on spans overlapping search range.

---

## CLIENT DELIVERY

- **Folder structure:** Delivery_YYYY-MM-DD_HHMM contains subfolders per property (sanitized name or "Unsorted"), each containing subfolders per doc type (Tenancy Agreements, Gas Safety Certificates, EICRs, EPCs, General Documents). PDFs named e.g. "12 Oak Street - Tenancy Agreement.pdf". Root: archive_data.json, viewer.html (with ARCHIVE_DATA embedded), [Client]_Document_Index_*.xlsx, optional Instructions.pdf (if instruction_sheet.pdf in project root).
- **archive_data.json:** client_name, generated_date, version "1.0", total_documents, properties → { category → [ { doc_id, doc_name, doc_type, filename, pdf_path, fields, full_text, quality_score, ocr_confidence } ] }.
- **viewer.html:** Copied from BASE; placeholder `window.ARCHIVE_DATA = null` replaced with embedded JSON (escape </script> in payload). Enables file:// use without fetch.
- **Instructions.pdf:** Copied from instruction_sheet.pdf in project root if present; not required.

---

## DOCUMENT TYPES

| Template file | doc_type | Field keys |
|---------------|----------|------------|
| tenancy_agreement.json | Tenancy Agreement | property_address, tenant_full_name, landlord_name, start_date, end_date, monthly_rent_amount, deposit_amount, agreement_date |
| gas_safety_certificate.json | Gas Safety Certificate | property_address, landlord_name, engineer_name, gas_safe_reg, inspection_date, expiry_date, appliances_tested, result, defects_noted |
| eicr.json | EICR | property_address, electrician_name, company_name, registration_number, inspection_date, next_inspection_date, overall_result, observations |
| epc.json | EPC | property_address, current_rating, potential_rating, date_of_assessment, valid_until, assessor_name, certificate_number |
| general_document.json | General Document | document_title, ocr_quality, searchable, notes |

Not yet built: Deposit Protection Certificate, Inventory/Check-in Report.

---

## PRICING / SALES / FINANCIAL (unchanged)

- Per-document pricing (~£2/doc assumption); local agency sales; bootstrapped; target £3k+/month.

---

## DECISIONS LOCKED IN

1. MVP-first; property/letting focus; human verification; per-doc pricing; local sales; deliverable = Excel + folders + viewer.
2. Camo then DSLR for capture.
3. Root path C:\ScanSystem_v2.

---

## IMMEDIATE ACTION ITEMS

1. Investigate [WinError 2] in pipeline.log if needed.
2. Stress-test with 5+ real documents.
3. One-page leave-behind; visit first 3 agencies.
4. Optionally add pdfplumber check to setup_check.bat.

---

## CHANGE LOG

| Date | What changed | Changed by |
|------|--------------|------------|
| 2026-02-23 | Initial PROJECT_BRAIN.md | Filip |
| 2026-02-23 | Code review; 5 templates, export, path/legacy notes | Claude |
| 2026-02-23 | auto_ocr_watch: multi-client; per-client logs | Claude |
| 2026-02-23 | ReviewStation rebuild; server endpoints; Export button | Claude |
| 2026-02-23 | Change history; layout, polling, PDF fit, UI polish | Claude |
| 2026-02-23 | PROJECT_BRAIN + SETUP_GUIDE + setup_check.bat to C:\ScanSystem_v2; flask/flask-cors | Claude |
| 2026-02-24 | review.json: scanned_at, exported_at; ReviewStation timeline column (Scan/Review/Export); export_client stamps exported_at | Claude |
| 2026-02-24 | ScanStation: full 3-column rebuild; left camera+queue, center preview+quality overlays+actions, right quality dashboard; quality analysis; Quick/Careful; naming; keyboard workflow; session stats; pipeline status | Claude |
| 2026-02-24 | PROJECT_BRAIN.md and SETUP_GUIDE.md updated to exact current state: all files, all API endpoints, all features, dependencies (flask, flask-cors), full folder structure C:\ScanSystem_v2; changelog updated; no deleted-file references | Claude |
| 2026-02-24 | Deleted design/spec HTML; ScanStation now auto-loads clients from GET /clients; ReviewStation adds OCR text viewer (pdfminer.six, /ocr-text), batch date filter, Re-process flow for Failed docs (/reprocess), and Export History from /exports; setup_check.bat and dependencies updated for pdfminer.six; PROJECT_BRAIN.md updated | Claude |
| 2026-02-28 | PROJECT_BRAIN.md updated by scanning actual codebase — all sections verified against live code: server endpoints (open-folder, delivery, raw-image, raw-list, rescan-queue), export (property→doc type, archive_data, viewer embed, pdfplumber, field extraction), ScanStation (queue from /docs, rescan panel, PDF toolbar hidden, viewer_url), ReviewStation (Sent to rescan, FitH, toolbar=0), viewer (Document/Details tabs, PDF.js, search highlight when HTTP), rescan workflow, Templates table, dependencies (pdfplumber added) | Cursor |
| 2026-02-23 | Five fixes: (1) ScanStation PDF preview: toolbar hidden via #toolbar=0&navpanes=0&view=FitH. (2) ScanStation: PROPERTY input with autocomplete (GET /docs/<client>, 300ms debounce), sessionStorage; auto-naming "Property - DocType N" per property+docType; .meta.json in raw/ with doc_name, property_address, doc_type_template; watcher reads .meta.json, writes doc_name and pre-fills property_address in review.json, uses doc_type_template, deletes .meta.json; server list_docs returns doc_name. (3) ScanStation: Session Summary in right panel (doc type counts, by-property breakdown). (4) ReviewStation: PDF preview loads immediately when entering View 3 (iframe src set in requestAnimationFrame). (5) Viewer: search-term highlighting in Details tab (full_text with <mark>) when opening from search; works from file://; Details tab shown by default when opening from search. | Cursor |
| 2026-02-23 | Viewer (FIX 3): PDF.js upgraded to 3.11.174; search term highlighted on PDF in Document tab (text layer + .pdf-search-highlight). When PDF.js fails (offline/file://), fallback to iframe and show note: "Open from the server URL..." or "Connect to internet for PDF search highlighting." | Cursor |
| 2026-02-23 | Rescan workflow rebuild — replace in place, no duplicates. Server: GET /doc-image, POST /rescan-replace (save new image to DOC folder, .reprocess trigger); POST /reprocess no longer copies to raw, accepts JSON body { reason }; GET /rescan-queue returns { queue } with doc_name, doc_type, reason, has_image. Watcher: check_reprocess_triggers() processes .reprocess in DOC folders, runs OCR in place, removes from rescan_queue. ScanStation: rescan panel shows per-doc cards with thumbnail, Rescan Now; rescan mode shows old image, Capture Replacement, Browse Files → /rescan-replace; Esc cancels. ReviewStation: Request re-scan opens reason modal (Blurry, Cropped, Wrong document, Too dark/light, Other), POST reason to /reprocess. | Cursor |
| 2026-02-23 | Added User_Guide folder for first-time users: README (overview, what is ScanStation/ReviewStation/Viewer, getting started), 01_ScanStation.md (capture, queue, rescan, export), 02_ReviewStation.md (dashboard, review, verify, request rescan, export), 03_Viewer.md (browse archive, search, delivery folder). | Cursor |
| 2026-02-23 | PROJECT_BRAIN.md fully rebuilt from codebase scan — all sections verified against actual code. API endpoints table with request/response details; processing and reprocessing pipelines step-by-step; ScanStation (layout, property naming, session summary, rescan panel, quality note, Quick/Careful, keyboard shortcuts, API calls); ReviewStation (views, status types, rescan modal, export, keyboard, API calls); Viewer (data load, tabs, search, offline/online, PDF.js). Rescan workflow and document unit clarified. | Cursor |
