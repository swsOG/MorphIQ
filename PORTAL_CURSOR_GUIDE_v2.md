# MORPH IQ PORTAL — CURSOR BUILD GUIDE (v2)

> **Philosophy:** Build only what's needed to land and serve your first 3 paying clients. Everything else waits until there's revenue. You are a solo operator — every session spent on features nobody's paying for is time stolen from selling.
>
> **Model guide for Cursor Composer:**
> - Sessions 1-3 (core functionality): **Opus** — backend logic, multi-file changes
> - Session 4 (AI chat): **Opus** — API integration
> - Session 5 (auth): **Opus** — security logic
> - Session 6 (visual polish): **Sonnet** — CSS/HTML, straightforward
> - Sessions 7+ (scale features): **Opus** — only when needed
>
> **The rule:** After Session 5, STOP BUILDING AND START SELLING. Sessions 6+ happen after you have at least one paying client.

---

## .cursorrules — PASTE THIS INTO C:\ScanSystem_v2\.cursorrules

```
# MORPH IQ — CURSOR RULES

## Project context
Morph IQ is a document scanning and compliance platform for UK letting agencies.
Solo operator business based in Harlow, Essex. No paying clients yet.
The product has three components:
1. ScanStation + ReviewStation (capture/review tools, HTML at project root)
2. Backend API server (server.py, port 8765)
3. Client Portal (portal_new/, Flask app, port 5000)

## Portal stack
- Flask + SQLite (portal.db) at C:\ScanSystem_v2\portal.db
- App: portal_new/app.py (no blueprints, no auth currently)
- Templates: portal_new/templates/ (portal.html, property.html, compliance.html)
- Static: portal_new/static/ (portal.css, portal.js, logo.png)
- Compliance engine: portal_new/compliance_engine.py
- Sync bridge: sync_to_portal.py (pipeline → portal.db)

## Portal API routes (app.py)
- GET / → portal.html (property archive + client picker when no ?client=)
- GET /compliance → compliance.html
- GET /property/<id> → property.html
- GET /api/clients → list clients
- DELETE /api/clients/<id> → remove client from portal.db
- GET /api/properties?client=X → property list with compliance pills
- GET /api/properties/<id> → property detail (compliance, deadlines, tenant, documents)
- GET /api/documents?q=&type=&status= → search/filter documents
- GET /api/documents/<source_doc_id> → single document with fields
- GET /api/compliance?client=X → { stats, actions, health_by_type }
- GET /api/stats → basic document counts
- PDFs served via ScanStation API: GET /pdf/<client>/<doc_id> on port 8765

## Database schema (portal.db)
- clients: id, name, slug, contact_email, contact_phone, is_active
- document_types: id, key, label, has_expiry, expiry_field_key, is_active
- properties: id, client_id, address, postcode, notes
- tenants: id, client_id, property_id, full_name, email, phone, tenancy_start, tenancy_end
- documents: id, client_id, property_id, document_type_id, source_doc_id, doc_name, status, pdf_path, raw_image_path, full_text, quality_score, reviewed_by, reviewed_at, scanned_at, batch_date
- document_fields: id, document_id, field_key, field_label, field_value, source
- compliance_records: id, client_id, property_id, document_id, record_type, expiry_date, status, details
CRITICAL: document_types uses `key` and `label` (not slug/name). properties uses `address` (not name).

## Compliance engine (compliance_engine.py)
Tracks 4 doc types: Gas Safety (gas_safety), EICR (eicr), EPC (epc), Deposit Protection (deposit).
Statuses: valid, expiring_soon (within 30 days), expired, missing.

## Code rules
- Dark theme: #060E10 bg, #0B1A1E elevated, #7AAFA6 accent
- Status colours: #10B981 valid, #F59E0B expiring, #EF4444 expired, #64748B missing
- All portal PDFs served via ScanStation API /pdf/<client>/<doc_id> on port 8765
- Don't modify server.py, auto_ocr_watch.py, scan_station.html, review_station.html, or export_client.py
- Only modify files inside portal_new/ unless explicitly told otherwise
```

---

## SESSION 1 — Make the dashboard actually useful
**What this solves:** Right now the dashboard shows properties but doesn't surface the most critical information — what's expiring, what's overdue, what needs action TODAY. This is the #1 thing an agency manager cares about.

### OPEN THESE FILES:
- portal_new/app.py
- portal_new/static/portal.js
- portal_new/templates/portal.html
- portal_new/compliance_engine.py

### PASTE INTO COMPOSER:
> I need to make the portal dashboard genuinely useful for a letting agency manager. Currently the dashboard shows a property list with compliance pills, but it doesn't surface urgent actions prominently.
>
> **Do these things in this order:**
>
> **1. Critical Expiries panel on the dashboard.**
> Add a right-hand panel (~35% width) next to the property/compliance matrix (~65%). This panel shows certificates expiring within 30 days or already expired. Data source: GET /api/compliance already returns an `actions` array with property, type, expiry_date, days_until_expiry, status, severity_text. Render each action as a card: document type (e.g. "Gas Safety CP12"), property address, countdown badge ("7 Days Left" in red, "12 Days Left" in amber), and a "View Property →" link that goes to /property/<id>. Header: "Critical Expiries" with item count. Scrollable. Show max 8, with "View all" link to /compliance page.
>
> **2. Portfolio stat cards at the top of the dashboard.**
> Four cards in a row above the main content: Total Properties (from properties count), Compliant (count where all 4 cert types are valid, show as % of total), Expiring Soon (count with any expiring_soon status), Non-Compliant (count with any expired or missing). Calculate these from the GET /api/properties response — each property already has gas_safety, eicr, epc, deposit status fields.
>
> **3. Compliance matrix — add health score column.**
> In the existing property table, add a HEALTH column. Health % = (number of valid cert types / 4) × 100 for each property. Display as coloured number: green if 100%, amber if 50-99%, red if below 50%.
>
> **4. AI chat bar at bottom of dashboard (visual placeholder only).**
> Below the main content, add a bar: lightning bolt icon, "Ask me about your portfolio compliance health...", text input, send button, chips "Summary Report" | "Missing Documents". Not functional yet — just the HTML/CSS. Will be wired in Session 4.
>
> Keep the existing client picker, property list, and all current functionality. This is additive.

### WHEN DONE — HANDOFF NOTES:
```
Session 1 completed: March 15, 2025

Files changed:

portal_new/templates/portal.html — Stat cards markup, two-column layout, Critical Expiries panel, Health column in table header, empty-state colspan, AI chat bar placeholder markup
portal_new/static/portal.js — updateStats() from allProperties, STATUS_KEYS, fetchCriticalExpiries(), renderCriticalExpiries(), Health column and colspan in renderTable() / showEmptyState(), init calls fetchCriticalExpiries() with fetchProperties()
portal_new/static/portal.css — Portfolio stat card variants (borders/subtitle), .content-columns / .content-left / .content-right, Critical Expiries panel and cards, .cell-health, AI chat bar and .portal-shell:has(.ai-chat-bar) .portal-main padding
What was built:

Portfolio compliance stat cards — Replaced the three cards with four: Total Properties, Fully Compliant (count + %), Expiring Soon, Non-Compliant; derived from allProperties (gas_safety, eicr, epc, deposit); green/amber/red left borders and accents.
Two-column layout + Critical Expiries panel — Main content split into ~65% (filter bar + property table) and ~35% (Critical Expiries). Panel loads via GET /api/compliance (with ?client= when set), shows expired/expiring_soon actions as clickable cards (type, address, badge, severity), max 8 items, “View all on Compliance page →”, and a green empty state when there are no critical items.
Health column — New column between Latest Activity and Compliance; health = (valid count / 4)×100 with 100% green, 50–99% amber, 0–49% red; empty-state colspan set to 6.
AI chat bar — Fixed bottom bar (visual only): lightning icon, disabled input “Ask about your portfolio compliance...”, disabled send button, “Summary Report” / “Missing Documents” chips, “Coming soon” label; only in the {% else %} block (client selected, not client picker).
Bugs/issues:
None observed; linter clean. Not tested in a running browser.

Decisions made:

Stats and Health computed client-side from allProperties and the four status fields (no new archive API).
Critical Expiries use existing GET /api/compliance; only expired and expiring_soon shown (no “missing” in this panel).
Archive stat cards scoped with .stats-row .stat-card so compliance page .stat-card styles are unchanged.
Type + address in Critical Expiry cards wrapped in .critical-expiry-text for correct flex stacking with the badge on the right.
Space under the fixed AI bar handled with .portal-shell:has(.ai-chat-bar) .portal-main { padding-bottom: 90px }.
Compliance “View all” URL built in JS from MORPHIQ_PORTAL.clientName to preserve ?client= when present.
```

---

## SESSION 2 — Search that actually works + document access improvements
**What this solves:** Agency managers need to find documents fast. "Show me the gas cert for 42 Oak Road" should take 2 seconds, not 2 minutes of clicking through properties.

### OPEN THESE FILES:
- portal_new/app.py
- portal_new/static/portal.js
- portal_new/static/portal.css
- portal_new/templates/portal.html
- portal_new/templates/property.html

### PASTE INTO COMPOSER:
> I need functional search and better document access across the portal.
>
> **1. Wire the search bar to GET /api/documents.**
> The search bar exists in the top bar of every page. When the user types 2+ characters, debounce 300ms, call GET /api/documents?q=<query>. Show results in a dropdown panel below the search bar (position absolute, dark card, max 8 results). Each result shows: document type, property address, date, status badge. Clicking a result navigates to /property/<property_id>?client=<client>&focus=<doc_type_slug>. Pressing Escape or clicking outside closes the dropdown. Store last 5 searches in localStorage, show them when the search input is focused with empty value.
>
> **2. Improve document drawer on property detail page.**
> When clicking a document on the property detail page, the drawer should open with: PDF preview on the left (~60%, using iframe src to ScanStation API /pdf/<client>/<doc_id> on port 8765), verified fields on the right (~40%, key-value list from the document's fields). Add a "Download PDF" button that opens the PDF URL in a new tab. Add a "View Full Screen" button that opens just the PDF in a new tab. Make sure the drawer can be closed with Escape key or clicking outside.
>
> **3. Add per-property document pack download.**
> On the property detail page, add a "Download All Documents" button. When clicked, POST to a new endpoint POST /api/properties/<id>/download-pack. Backend: query all documents for this property, create a ZIP file in memory (using Python zipfile module) containing all PDFs (fetched from their pdf_path), return the ZIP as a downloadable response. Filename: "<PropertyAddress>_Documents.zip".

### WHEN DONE — HANDOFF NOTES:
```
Session 2 completed: March 15, 2025

Files changed:

portal_new/app.py — Added d.property_id to api_documents() SELECT; added POST /api/properties/<int:property_id>/download-pack (ZIP build, send_file), plus io, re, zipfile imports.
portal_new/static/portal.js — Search dropdown: getRecentSearches, saveRecentSearch, fetchSearchDocuments, renderSearchResults, renderRecentSearches, initSearchDropdown, closeSearchDropdown; init() calls initSearchDropdown() when .search-container exists. Drawer: closeDrawer/selectDocument toggle #detail-drawer-wrapper; renderDrawer branches to renderDrawerSplit(doc) when .drawer-split-left exists; renderDrawerSplit fills PDF panel, doc header, Core Info, Verified Fields, Download/Full Screen; overlay click-to-close in initPropertyPage. Download pack: click handler for #property-download-pack (loading state, POST, blob download from Content-Disposition).
portal_new/static/portal.css — Search dropdown styles (.search-dropdown, .search-dropdown-row, recent, empty). Property drawer: .detail-drawer-wrapper, .drawer-overlay, .detail-drawer-split, split left/right, PDF container, panel scroll, doc header, sections, field list, actions. .property-actions gap and .btn-download-pack.
portal_new/templates/portal.html — (Session 2.1: no template change for search dropdown; dropdown is created in JS.)
portal_new/templates/property.html — Drawer replaced with split-panel markup (wrapper, overlay, drawer-split-left, drawer-split-right, doc header, Core Info, Verified Fields, Download PDF / View Full Screen). "Download All Documents" button added in .property-actions.
What was built:

Session 2.1 — Live search dropdown
Typing 2+ chars (300ms debounce) calls GET /api/documents?q=…&limit=8. Results in a dropdown under .search-container (API-driven). Each row: doc icon, type (bold), property address (muted), date, status badge; click → /property/<property_id>?focus=<doc_type_slug> (keeps ?client=). Escape / click-outside close dropdown. Empty results: "No documents found." Recent searches when input focused and empty (last 5 from localStorage key morphiq_recent_searches), with "Recent" and "Clear"; running a search adds query to front (deduped, max 5). On archive, local property filter and API dropdown both run. Backend: api_documents() now includes property_id in the SELECT.

Session 2.2 — Split-panel document drawer (property page)
Tabbed drawer replaced with side-by-side: left ~55% full-height PDF iframe (http://127.0.0.1:8765/pdf/<client>/<doc_id>#zoom=page-width&view=FitH) or placeholder; right ~45% scrollable panel with doc header (icon, name, source_doc_id, status), "Core Info" (client, property, scanned, batch), "Verified Fields" (from doc.fields), and actions "Download PDF" and "View Full Screen." Drawer width min(900px, 70vw); overlay + ✕ close; Escape and click-outside (overlay) close. Archive drawer in portal.html unchanged.

Session 2.3 — Per-property document pack ZIP
Backend: POST /api/properties/<property_id>/download-pack builds ZIP from all property PDFs under BASE_DIR/Clients/<client_name>/<pdf_path>, organized as <DocTypeLabel>/<source_doc_id>.pdf; returns 404 JSON if no documents or no PDFs on disk; download_name = sanitized property address + _Documents.zip. Frontend: "Download All Documents" in property header; click shows "Preparing ZIP…" (disabled), POSTs, on success downloads blob using filename from Content-Disposition, on failure alerts; button state restored in finally.

Bugs/issues:
None reported. Not run in a browser; Content-Disposition parsing and ZIP path building are untested in live environment.

Decisions made:

Search dropdown is global (all pages with .search-container); archive keeps existing local filter; both run when typing on archive.
Drawer behavior is chosen by DOM: if .drawer-split-left exists, renderDrawer uses renderDrawerSplit; otherwise keeps legacy tabbed behavior for archive.
Download-pack uses POST (no idempotent GET with side-effect). ZIP is built in memory; doc type label sanitized for folder names; filename in ZIP uses source_doc_id for uniqueness.
Property address for ZIP name sanitized with [^a-zA-Z0-9]+ → _; doc type label for ZIP paths uses [\w\s-] only to avoid path separators.
No changes to server.py, compliance_engine.py, portal.html, or compliance.html per instructions.
```

---

## SESSION 3 — Document upload + notification bell
**What this solves:** Clients need to be able to upload new certificates themselves (self-service renewals). And the notification bell needs to actually show alerts.

### OPEN THESE FILES:
- portal_new/app.py
- portal_new/static/portal.js
- portal_new/static/portal.css
- portal_new/templates/portal.html
- portal_new/templates/property.html
- portal_new/templates/compliance.html

### PASTE INTO COMPOSER:
> I need document upload and working notifications.
>
> **1. Document upload — client self-service.**
> Add an "Upload Document" button on: the property detail page (uploads to that property) and the compliance dashboard (user selects which property). Clicking opens a modal: select property (dropdown from user's properties — skip if already on a property page), select document type (Gas Safety Certificate, EICR, EPC, Deposit Protection, Tenancy Agreement, Other), file picker (accepts .pdf, .jpg, .jpeg, .png, .tiff, max 20MB), optional notes field, Submit button.
>
> Backend: POST /api/documents/upload — accepts multipart form data (file + property_id + document_type + notes). Saves the file to the appropriate client's Clients/<ClientName>/raw/ folder (lookup client name from property's client_id). Also writes a .meta.json sidecar next to the file with: doc_name (generated from property address + doc type), property_address (from properties table), doc_type_template (the selected type). The existing watcher (auto_ocr_watch.py) will automatically pick up the file, OCR it, run AI prefill, and it'll appear in the portal after sync.
>
> After upload, show a success message: "Document uploaded. It will appear in your portal within 1-2 minutes after processing." Don't poll — keep it simple.
>
> **2. Notification bell — wire to compliance data.**
> The bell icon exists in the top bar. On page load, fetch GET /api/compliance and count the total actions (expired + expiring_soon + missing). Display this count as a red badge on the bell. Clicking the bell opens a dropdown showing the top 5 actions (same format as critical expiries panel cards: type, property, countdown). "View all" link goes to /compliance page. No separate alerts table needed — the compliance engine already calculates this on every request.
>
> File validation: check file extension and size client-side before upload. Show inline error messages for invalid files.

### WHEN DONE — HANDOFF NOTES:
```
Session 3 completed: [date]
Files changed: [list]
What was built:
- [ ] Upload modal and backend endpoint
- [ ] File saves to raw/ with .meta.json for watcher
- [ ] Notification bell wired to compliance actions
Bugs/issues:
Decisions made:
```

---

## SESSION 4 — AI chat assistant
**What this solves:** The "Morph IQ Insights" differentiator. No other scanning company gives you an AI you can ask "which properties have overdue gas certs?" and get an instant answer from your own data.

### OPEN THESE FILES:
- portal_new/app.py
- portal_new/static/portal.js
- portal_new/templates/portal.html

### PASTE INTO COMPOSER:
> I need to make the AI chat bar on the dashboard functional. It should use the Claude API to answer questions about the client's portfolio using their real data from portal.db.
>
> **1. Backend: POST /api/chat**
> Accepts JSON body: { "message": "..." }. On the backend:
> - Get the current client from the ?client= parameter (or session, if auth exists by now)
> - Query portal.db for: total properties, compliance stats (from compliance_engine.evaluate_compliance()), list of all properties with their compliance statuses, list of all expiring/expired actions with dates, list of all tenants with rent amounts and tenancy dates, total document counts by type
> - Build a Claude API call using the ANTHROPIC_API_KEY environment variable (already used by ai_prefill.py)
> - System prompt: "You are the Morph IQ compliance assistant for [client_name]. You have access to their complete property portfolio data. Answer questions about compliance status, expiry dates, document details, tenants, and portfolio health. Be specific — reference actual property addresses, dates, amounts, and certificate details from the data. Keep answers concise and actionable. If asked about something not in the data, say so."
> - User message: the chat input text
> - Include the portfolio data as a structured context block in the user message
> - Model: claude-sonnet-4-20250514 (fast, cheap for chat)
> - max_tokens: 1000
> - Return: { "response": "..." }
>
> **2. Frontend: wire the chat bar.**
> When user types a message and hits Enter or clicks Send:
> - Show a loading indicator (pulsing dots or spinner)
> - POST to /api/chat with the message
> - Display the response in a chat bubble above the input bar (dark card, teal left border, markdown rendered)
> - Keep the last 5 messages visible in the chat area (session only, cleared on page refresh)
> - Quick action chips: "Summary Report" sends "Give me a portfolio compliance summary with key numbers and urgent actions", "Missing Documents" sends "Which properties are missing required certificates? List each one with what's missing."
> - Error handling: if the API call fails, show "Unable to connect to Morph IQ Intelligence. Please try again."
>
> **3. Suggested questions.**
> When the chat area is empty (no messages yet), show 3-4 suggested questions as clickable pills:
> - "What's expiring this month?"
> - "Which properties are non-compliant?"
> - "Portfolio health summary"
> - "List all tenants and rents"

### WHEN DONE — HANDOFF NOTES:
```
Session 4 completed: [date]
Files changed: [list]
What was built:
- [ ] POST /api/chat endpoint with Claude integration
- [ ] Portfolio data context injection
- [ ] Chat UI with messages, loading, error states
- [ ] Quick action chips and suggested questions
Bugs/issues:
Decisions made:
```

---

## SESSION 5 — Authentication (basic login)
**What this solves:** You can't give a client access to the portal without a login. This is the minimum security needed to deploy.

### OPEN THESE FILES:
- portal_new/app.py
- portal_new/static/portal.css
- portal_new/templates/ (all templates)

### PASTE INTO COMPOSER:
> I need basic authentication on the portal. Keep it simple — this is for deploying to my first 1-3 agency clients, not enterprise scale.
>
> **1. Database: add users table.**
> Create a migration script (portal_new/migrate_add_users.py) that adds to portal.db:
> - `users` table: id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, full_name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'manager' (values: 'admin' or 'manager'), client_id INTEGER (nullable — NULL for admin, FK to clients.id for managers), is_active INTEGER DEFAULT 1, created_at TEXT, last_login TEXT
> - Don't create employee role or property assignment table yet. That's future scope.
> - Script must be safe to run multiple times (check if table exists first).
>
> **2. Seed script.**
> Create portal_new/seed_admin.py: creates admin user (filip@morphiq.co.uk, password from input prompt, role=admin, client_id=NULL). Also creates one demo manager user for testing (demo@harlow-agency.co.uk, role=manager, client_id=1).
>
> **3. Authentication in app.py.**
> - Add flask-login. User class that loads from portal.db users table.
> - POST /login: validate email + password (werkzeug check_password_hash). On success, login_user() and redirect to /. On failure, re-render login with error.
> - GET /logout: logout_user(), redirect to /login.
> - @login_required on all page routes (/, /compliance, /property/<id>) and all API routes (/api/*).
> - For admin users (role=admin, client_id=NULL): show client picker as before, use ?client= to scope.
> - For manager users (role=manager, client_id set): skip client picker, auto-scope everything to their client_id. Remove ?client= dependency — get client from current_user.client_id.
> - Session secret from environment variable PORTAL_SECRET_KEY with a fallback default for dev.
>
> **4. Login page.**
> Create portal_new/templates/login.html. Dark theme matching portal (same colours, same font). Morph IQ logo centred at top. Email + password fields. "Sign in" button (teal accent). Error message area. Clean, minimal, professional. No "forgot password" or "register" — those are manual for now.
>
> **5. Update all templates.**
> Show current user's name in the top bar (replacing the placeholder). Show "Sign out" link. For managers, don't show the client picker or client switch control — they only see their own data.

### WHEN DONE — HANDOFF NOTES:
```
Session 5 completed: [date]
Files changed: [list]
What was built:
- [ ] Users table migration
- [ ] Admin + demo manager seed
- [ ] Flask-Login integration
- [ ] Login page
- [ ] All routes protected
- [ ] Manager auto-scoping (no client picker)
Admin login: filip@morphiq.co.uk / [password]
Demo manager: demo@harlow-agency.co.uk / [password]
Bugs/issues:
Decisions made:
STATUS: PORTAL IS DEPLOYABLE. Stop here and sell.
```

---

## ⚠️ STOP POINT — GO SELL

After Session 5, you have:
- ✅ Dashboard with stats, compliance matrix, critical expiries, AI chat bar
- ✅ Working search across all documents
- ✅ Document drawer with PDF preview and verified fields
- ✅ Document upload (client self-service)
- ✅ Property detail with compliance cards, deadlines, tenant info
- ✅ Compliance dashboard with action list and health table
- ✅ Notification bell with alert count
- ✅ AI chat assistant answering questions from real portfolio data
- ✅ Login system (admin + manager roles)
- ✅ Per-client data isolation

**This is enough to charge money.** Visit agencies, demo the portal, sign contracts.

The sessions below are for AFTER you have paying clients and know what they actually need.

---

## SESSION 6 — Visual polish (POST-REVENUE)
**When to do this:** After you have at least 1 signed client. They're using the portal and you want it to feel more premium.

### OPEN THESE FILES:
- portal_new/static/portal.css
- All templates
- Stitch screenshots

### PASTE INTO COMPOSER:
> I have a working portal with paying clients. Now I need to polish the visual design to match these Stitch screenshots [attach screenshots]. Don't change any backend code or JavaScript logic. Only CSS and HTML templates.
>
> [Paste the specific visual changes you want — sidebar reskin, card styling, typography, animations, etc. Use the Phase 1 detail from the original build plan.]

---

## SESSION 7 — Employee roles + property assignment (POST-REVENUE)
**When to do this:** When a client says "I need my negotiators to only see their own properties."

### PASTE INTO COMPOSER:
> I need to add an employee role to the portal auth system. [Use Phase 2.4-2.6 detail from original plan, but only when a real client requests it.]

---

## SESSION 8 — Email notifications (POST-REVENUE)
**When to do this:** When clients say "Can I get an email when something's about to expire?"

---

## SESSION 9 — Settings page (POST-REVENUE)
**When to do this:** When you or clients need configurable preferences.

---

## SESSION 10 — Export/reporting (POST-REVENUE)
**When to do this:** When clients need compliance reports for audits or landlord reporting.

---

## SESSION 11 — GDPR + audit trail (POST-REVENUE)
**When to do this:** When you're handling enough client data that formal compliance matters, or when a client's legal team asks for it.

---

## SESSION 12 — Production deployment (POST-REVENUE)
**When to do this:** When you need the portal accessible outside your local network.

---

## HANDOFF LOG — KEEP THIS UPDATED

Paste your handoff notes from each session below. When opening a new Cursor session or Claude chat, give it the most recent entry plus the .cursorrules.

### Session 1:
```
[paste here after completing]
```

### Session 2:
```
[paste here after completing]
```

### Session 3:
```
Session 3 completed: 2026-03-15
Files changed: portal_new/app.py, portal_new/static/portal.js, portal_new/static/portal.css, portal_new/templates/portal.html, portal_new/templates/property.html, portal_new/templates/compliance.html
What was built:
- [x] POST /api/documents/upload endpoint — saves to raw/ with .meta.json sidecar
- [x] Upload modal on property detail page (pre-selected property)
- [x] Upload modal on compliance page (with property dropdown)
- [x] Client-side file validation (extension + 20MB size limit)
- [x] Notification bell in header across all pages
- [x] Bell badge with compliance action count
- [x] Bell dropdown with top 5 urgent items + navigation
Bugs/issues: None.
Decisions made: Upload saves to raw/ and relies on existing watcher pipeline for processing. No polling for upload status — user sees a "1-2 minutes" message. Bell fetches compliance data fresh on each page load rather than caching.
```

### Session 4:
```
Session 4 completed: 2026-03-15
Files changed: portal_new/app.py, portal_new/static/portal.js, portal_new/static/portal.css, portal_new/templates/portal.html
What was built:
- [x] POST /api/chat endpoint with Claude API integration (Sonnet model)
- [x] Portfolio data context injection (properties, compliance statuses, tenants, document counts, urgent actions)
- [x] Chat bar UI at bottom of dashboard with input, send button, lightning bolt icon
- [x] Message display — user right-aligned, assistant left-aligned with teal border
- [x] Loading state with pulsing dots animation
- [x] Quick action chips (Summary Report, Missing Documents)
- [x] Suggested questions shown when chat is empty (4 clickable pills)
- [x] Error handling for API failures
Bugs/issues: [fill in any bugs you encountered]
Decisions made: Using claude-sonnet-4-20250514 for chat (fast + cheap). Max 5 messages visible per session, not persisted. Portfolio data re-queried on every chat message (no caching) to ensure freshness. Plain text responses only — no markdown rendering.
```

### Session 5:
```
Session 5 completed: 2026-03-15
Files changed: portal_new/app.py, portal_new/static/portal.css, portal_new/templates/portal.html, portal_new/templates/property.html, portal_new/templates/compliance.html, portal_new/templates/login.html (new), portal_new/migrate_add_users.py (new), portal_new/seed_admin.py (new)
What was built:
- [x] Users table migration script (safe to re-run)
- [x] Admin + demo manager seed script
- [x] Flask-Login integration with session auth
- [x] Login page (dark theme, Morph IQ branded)
- [x] All page routes and API routes protected with @login_required
- [x] Manager auto-scoping (no client picker, data locked to their client)
- [x] Admin sees everything with client picker
- [x] User name initial in header, Sign out link
Bugs/issues: [fill in any bugs you encountered]
Decisions made: Using flask-login with server-side sessions. Admin email: filip@morphiq.co.uk. Managers auto-scoped by client_id. No forgot-password or registration — manual account creation only for now.
Admin login: filip@morphiq.co.uk / [your password]
Demo manager: demo@agency.co.uk / demo123
STATUS: PORTAL IS DEPLOYABLE. Core build complete.
```

---

## PROGRESS TRACKER

| Session | What | Status | Revenue-blocking? |
|---------|------|--------|-------------------|
| 1 | Dashboard upgrades (expiries, stats, health) | ☐ | YES |
| 2 | Search + document access + download | ☐ | YES |
| 3 | Document upload + notification bell | ☑ | YES |
| 4 | AI chat assistant | ☑ | YES (differentiator) |
| 5 | Authentication (login, roles) | ☑ | YES |
| 6 | Visual polish | ☐ | No — nice to have |
| 7 | Employee roles | ☐ | No — when requested |
| 8 | Email notifications | ☐ | No — when requested |
| 9 | Settings page | ☐ | No — when requested |
| 10 | Export/reporting | ☐ | No — when requested |
| 11 | GDPR/audit | ☐ | No — when scale demands |
| 12 | Production deployment | ☐ | No — when going online |

**5 sessions to a sellable product. Everything after that is driven by client feedback, not speculation.**
