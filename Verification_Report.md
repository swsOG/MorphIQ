# Morph IQ — Technical Claims Verification Report

Generated 2026-04-11 against the live codebase in `Product/`.

---

## Architecture Claims

**1. The system has 6 core components: ScanStation, Processing Pipeline, AI Prefill, ReviewStation, Client Portal, RAG-powered AI Chat**

- **CONFIRMED**
- Evidence: `scan_station.html` (ScanStation), `auto_ocr_watch.py` (Processing Pipeline), `ai_prefill.py` (AI Prefill), `review_station.html` (ReviewStation), `portal_new/app.py` (Client Portal, 4966 lines), `portal_new/app.py:4511` (`/api/chat` RAG endpoint).

**2. The portal has 8 pages: Overview, Properties, Compliance, Documents, Packs, Ask AI, Reports, Settings**

- **CONFIRMED**
- Evidence: `portal_new/app.py` route decorators at lines 868 (`/overview`), 884 (`/properties`), 954 (`/compliance`), 900 (`/documents`), 914 (`/packs`), 1198 (`/ask-ai`), 928 (`/reports`), 1175 (`/settings`).

**3. There are 35+ API endpoints across server.py and portal_new/app.py combined**

- **CONFIRMED** — actually significantly more.
- Evidence: `server.py` exposes 21 unique routes (lines 156–850); `portal_new/app.py` exposes ~57 routes (lines 780–4511). Combined total ≈ 78 endpoints.

**4. The system handles 6 document types: Gas Safety, EICR, EPC, Tenancy Agreement, Deposit Protection, Inventory**

- **CONFIRMED**
- Evidence: `ai_prefill.py:345` `RECOGNIZED_DOC_TYPES` lists exactly these six. `sync_to_portal.py:25` `DOC_TYPE_MAP` also lists six. Note: per `docs/PROJECT_BRAIN.md:46`, Deposit Protection and Inventory are recognized doc types but their JSON field templates are placeholders only.

---

## RAG Claim

**5. The `/api/chat` endpoint retrieves properties, compliance statuses, tenant details, document counts, and action items from portal.db, injects them as structured context into the Claude API prompt, and generates grounded responses — i.e. this is a RAG implementation**

- **CONFIRMED**
- Evidence: `portal_new/app.py:4511–4919` (`api_chat`):
  - `total_properties_row` and `properties_rows` queried (lines 4564–4587).
  - Compliance per property via `compliance_engine.evaluate_compliance()` (line 4591).
  - Tenant snapshots from latest Tenancy Agreement + `document_fields` (lines 4617–4699).
  - `doc_type_counts` aggregated from `documents` (line 4702).
  - `actions` list (expired/expiring/missing) built with severity copy (lines 4736–4853).
  - All packed into `portfolio_context` dict (line 4855), serialized to JSON, wrapped in `<portfolio_data>` tags inside `user_content` (line 4881), and sent to `client.messages.create(model="claude-sonnet-4-20250514", ...)` with a system prompt instructing Claude to ground responses in the data (lines 4866–4901). This is a textbook retrieval-augmented generation pattern.

---

## AI / Pipeline Claims

**6. AI prefill uses Claude API for document classification via fuzzy matching**

- **CONFIRMED**
- Evidence: `ai_prefill.py:476–479` `detect_doc_type_from_pdf` calls Claude. Normalization at `ai_prefill.py:465–473` (`_normalize_doc_type`) uses substring `in` matching against `RECOGNIZED_DOC_TYPES`, not exact equality. PROJECT_BRAIN locks this in as decision #6: "AI doc-type matching is **contains**-based, not exact string equality".

**7. There are type-specific extraction prompts for each document type**

- **CONFIRMED**
- Evidence: `ai_prefill.py` defines six prompt builders: `build_tenancy_agreement_prompt` (line 84), `build_gas_safety_prompt` (line 117), `build_eicr_prompt` (line 147), `build_epc_prompt` (line 179), `build_deposit_protection_prompt` (line 205), `build_inventory_prompt` (line 233). Wired in `DOC_TYPE_CONFIG` at line 364.

**8. Completeness scoring calculates a 0-100% score per document**

- **CONFIRMED**
- Evidence: `ai_prefill.py:414–444` `compute_quality_assessment` — `score = int((filled / total) * 100)`.

**9. needs_attention flag is set when score is below 70% or property_address is missing**

- **CONFIRMED**
- Evidence: `ai_prefill.py:444` — `review["needs_attention"] = (not property_address) or (score < 70)`.

**10. The file watcher polls the raw/ folder every 2 seconds**

- **CONFIRMED**
- Evidence: `auto_ocr_watch.py:640` — `time.sleep(2)` at the bottom of the main `while True` loop in `main()`.

**11. Pipeline is: ImageMagick preprocessing → Tesseract/OCRmyPDF → searchable PDF**

- **CONFIRMED**
- Evidence: `auto_ocr_watch.py:423–439` `preprocess_for_ocr` calls ImageMagick (`MAGICK` constant pointing to `magick.exe`) with grayscale, deskew, contrast-stretch, sharpen flags. `auto_ocr_watch.py:441–454` `ocr_to_pdf` calls `ocrmypdf` with `--tesseract-pagesegmode 4 -l eng` and writes a searchable PDF.

---

## ReviewStation Claims

**12. Documents with needs_attention=true sort to the top with an amber indicator**

- **CONFIRMED**
- Evidence: `review_station.html:1153–1154` sort comparator places `needs_attention === true` ahead of others. `review_station.html:1330` renders an `attention-dot` span when `doc.needs_attention === true`. Amber palette defined at line 28 (`--amber: #f5a623`).

**13. Missing fields are highlighted with an amber border**

- **CONFIRMED**
- Evidence: `review_station.html:695–698` — `.field-group.field-attention input { border-left: 4px solid var(--amber); }`. Class applied at line 1459 (`isMissing ? " field-attention" : ""`). A "AI could not extract — please fill manually" hint is also shown at line 1463.

**14. Verification gate blocks marking a document as Verified if property_address is empty**

- **CONFIRMED**
- Evidence: `review_station.html:1608` — `errDiv.textContent = "Property address is required before verification.";` blocks the save path.

**15. Merge capability: select 2+ documents, merge PDFs via pypdf, AI prefill re-runs**

- **CONFIRMED**
- Evidence: `server.py:41` — `from pypdf import PdfReader, PdfWriter`. `server.py:738–847` `merge_docs` route: writes `merged_<base_doc_id>.pdf` (line 776–778), updates `base_review["files"]["pdf"]` (line 805), then "AI prefill on merged doc (best-effort)" at line 824 followed by portal sync at line 827. Frontend modal at `review_station.html:940–948`, submit handler `submitMerge` at line 1792.

**16. Split capability: split multi-page document into separate DOC records**

- **CONFIRMED**
- Evidence: `server.py:850–949` `split_doc` route. Refuses if `page_count == 1` (line 867). Creates new DOC IDs per page with notes "Split from {doc_id} (page {i+1})" (line 910), then portal-syncs each (line 934). Frontend trigger at `review_station.html:859` `splitCurrentDoc()`, button only shown when `(doc.page_count || 1) > 1` (line 1432).

---

## Portal Claims

**17. Role-based access: admin vs manager with client_id scoping**

- **CONFIRMED**
- Evidence: `portal_new/app.py:4550–4556` distinguishes `role == "manager"` (locked to assigned `client_id`) from admin (can pass `client` in payload/query). PROJECT_BRAIN decision #26 documents the model. Admin-only routes guarded e.g. `/admin/clients` (line 1730), `/admin/users` (line 1758), `/api/compliance/actions/resolved` (line 4498 — `role != "admin"` returns 403).

**18. Compliance engine evaluates 4 certificate types (gas, EICR, EPC, deposit)**

- **CONFIRMED**
- Evidence: `portal_new/app.py:4716` — `TYPES = ["gas_safety", "eicr", "epc", "deposit"]`. Confirmed by PROJECT_BRAIN line 223: `compliance_engine.evaluate_compliance()` ... four types.

**19. Expiry tracking at 30/60/90 day intervals**

- **PARTIALLY TRUE**
- Evidence: `portal_new/compliance_engine.py:44` — only `EXPIRING_SOON_DAYS = 30`. No 60-day or 90-day thresholds exist; grep for `60` and `90` in `compliance_engine.py` returned no matches.
- Correction: There is a single 30-day "expiring soon" threshold. Status states are `valid` / `expiring_soon` / `expired` / `missing`. Day-counts are computed for display (e.g. "Expires in N days") but there are no 60- or 90-day tier breakpoints in the rules engine.

**20. Document packs with full CRUD API and ZIP/PDF export**

- **CONFIRMED**
- Evidence: `portal_new/app.py` — `GET /api/packs` (2790), `POST /api/packs` (2821), `GET /api/packs/<id>` (2857), `PUT /api/packs/<id>` (2926), `DELETE /api/packs/<id>` (2956), add document (2978), remove document (3027), reorder (3066), `GET /api/packs/<id>/export/zip` (3133), `GET /api/packs/<id>/export/pdf` (3179).

**21. Server-side search with debounced frontend (300ms)**

- **PARTIALLY TRUE**
- Evidence: `portal_new/static/portal.js:239` — `SEARCH_DROPDOWN_DEBOUNCE_MS = 300` for the global search dropdown (line 359). However, the documents-page filter uses `searchDebounce = setTimeout(() => applyFilters(), 150);` at line 2050.
- Correction: The 300 ms debounce applies to the global header search dropdown. The Documents page filter input is debounced at 150 ms. Server-side `?q=` search itself is confirmed (PROJECT_BRAIN decision #18).

---

## Infrastructure Claims

**22. sync_to_portal.py is the sole bridge from filesystem review.json to portal.db**

- **CONFIRMED**
- Evidence: PROJECT_BRAIN decision #9 locks this in. `auto_ocr_watch.py:11` imports only `sync_single_doc` from `sync_to_portal`. `server.py` uses the same `sync_single_doc` after merge/split/review operations. No raw `INSERT INTO documents` exists in the watcher.

**23. No direct portal.db inserts in the watcher — all go through sync_single_doc**

- **CONFIRMED**
- Evidence: `auto_ocr_watch.py:233` (`process_group`) and `auto_ocr_watch.py:577` (`process_file`) call `sync_single_doc(client_name, doc_id)` only. No `sqlite3` import or direct DB connection in `auto_ocr_watch.py`.

**24. Batch processing: bulk_import.py for stress testing, rerun_prefill.py for batch AI re-processing with 429 retry logic**

- **CONFIRMED**
- Evidence: `scripts/bulk_import.py` defines stress-test client configs (50–400 docs across 5 fictional agencies, lines 34–40). `scripts/rerun_prefill.py:51–75` `run_ai_prefill_subprocess` retries up to 3 times and waits 60 s when stdout contains `"429"` (line 66). Note: both files live under `Product/scripts/`, not the project root as PROJECT_BRAIN's "Core layout" diagram suggests.

**25. Environment variables loaded from .env (ANTHROPIC_API_KEY, PORTAL_SECRET_KEY)**

- **PARTIALLY TRUE**
- Evidence: `ai_prefill.py:12–21` and `auto_ocr_watch.py:13–22` both contain a hand-rolled `.env` parser (`python-dotenv` is intentionally not installed — see PROJECT_BRAIN known issues). `ANTHROPIC_API_KEY` is read in `ai_prefill.py:263`. `PORTAL_SECRET_KEY` could not be confirmed in this verification pass.
- Correction: The `.env` loader is real and `ANTHROPIC_API_KEY` is confirmed. The presence of `PORTAL_SECRET_KEY` specifically in `.env` was not verified — reword as "loads secrets such as `ANTHROPIC_API_KEY` from `.env`".

---

## Prompt Engineering Claim

**26. There is a four-tool prompt system (Architect, Packager, Auditor, System Reviewer)**

- **FALSE**
- Evidence: Grep for `Architect`, `Packager`, `Auditor`, `System Reviewer`, `four-tool`, `four_tool` across `Product/` returned only `README.md:9 ## Architecture` and an unrelated RTF reference. No such tooling exists in the Morph IQ codebase. (It may exist in the user's broader workflow / `PROMPT_LIBRARY.md` outside `Product/`, but it is not part of the product itself — do not list it as a Morph IQ feature.)

---

## ScanStation Claims

**27. Multi-page capture with Add Page button and P keyboard shortcut**

- **CONFIRMED**
- Evidence: `scan_station.html:1041` — `<button ... id="btnAddPage">📄 Add Page</button>`. `scan_station.html:1059` — `<span><kbd>P</kbd> Add Page</span>` in the keyboard hints panel. Keydown handler at line 3053.

**28. Group completion via Finish Document button or Escape key**

- **CONFIRMED**
- Evidence: `scan_station.html:1014` (top "Finish Document" button), `scan_station.html:1042` (`btnFinishDoc`), and the keydown handler at `scan_station.html:3073` — `if (e.key === "Escape" && multiPageState.isMultiPage) { ... }`.

**29. Session Intelligence panel exists**

- **PARTIALLY TRUE**
- Evidence: `scan_station.html:1090–1093` — the panel is labelled "Live Session Summary" in the HTML, not "Session Intelligence". `docs/PROJECT_BRAIN.md:35` calls it "Live Session Intelligence" — internal naming mismatch.
- Correction: The panel exists and shows live session aggregates (counts, doc types, property groupings). Use the in-app label "Live Session Summary" on your CV/portfolio for accuracy, or describe it as "Live Session Summary panel".

**30. Camera controls via MediaStream API**

- **CONFIRMED**
- Evidence: `scan_station.html:1764` and `1822` — `navigator.mediaDevices.getUserMedia({ video: true })` / `getUserMedia(constraints)`. Standard MediaStream API.

---

## Additional Features Found

Things in the codebase worth flagging that the claim list did not cover:

- **Soft-delete + 30-day purge for clients** — `portal_new/soft_delete.py` plus startup hook `purge_expired_soft_deletes` at `app.py:4951` enforce a retention window.
- **Activity log** with `log_activity()` calls across compliance, settings, and admin routes (`/api/activity` at line 1575). Auditable trail of who resolved/snoozed/created what.
- **Compliance actions: resolve + snooze workflow** — `/api/compliance/actions/resolve` (4359) and `/api/compliance/actions/snooze` (4424) with `ON CONFLICT ... DO UPDATE` upserts and a 1–730 day snooze window.
- **PDF compliance reports** rendered server-side via ReportLab — `_generate_compliance_pdf` (~line 4250+) and `/api/compliance/report` route, returning a branded PDF with property table, status colour coding, and actions list.
- **PDF route security** — `/pdf/<path>` (1215) and `/pdf-by-id/<source_doc_id>` (1247) both `@login_required` AND tenant-scoped via JOIN to `clients` table (fixed 2026-04-06 per PROJECT_BRAIN).
- **Reprocess trigger files** — operators can drop a `.reprocess` marker into a DOC folder and the watcher will re-OCR in place (`auto_ocr_watch.py:457–526`).
- **Stale document cleanup** — `sync_portal_for_clients` deletes portal records whose DOC folders no longer exist on disk (`sync_to_portal.py:398–459`), and removes orphan properties.
- **Property address inference + postcode extraction** — `ensure_property` in `sync_to_portal.py:76–110` extracts the last comma-separated token as a UK postcode automatically.
- **Multi-page group atomic processing** — `process_group` (`auto_ocr_watch.py:122`) merges N preprocessed PNGs into a single multi-page TIFF, runs one OCRmyPDF pass, then writes one DOC record with `page_count` and `raw_images[]`.
- **Property-anchored chat citations** — system prompt at `app.py:4866` instructs Claude to emit `[[address|PROPERTY_ID]]` and `[[address > Gas Safety|PROPERTY_ID:gas_safety]]` link tokens, enabling click-through from chat answers to portal pages. This is a nice "RAG with citations" touch beyond plain retrieval.
- **Pack export to both ZIP and merged PDF** — pypdf-based PDF concatenation across pack documents (`/api/packs/<id>/export/pdf`).
- **Bulk_import stress harness** — `scripts/bulk_import.py` can spin up 5 fake agencies with 50–400 documents each for load testing, reusing the real watcher pipeline (`preprocess_for_ocr`, `ocr_to_pdf`, `run_ai_prefill`).
