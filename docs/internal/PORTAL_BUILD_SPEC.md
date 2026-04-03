# MORPH IQ — Portal Build Specification
> **Purpose:** This document is the complete technical specification for building the Morph IQ client portal. Paste this into a new Claude or Cursor session to start building. Everything you need is here — no clarifying questions required.

---

## 1. WHO YOU'RE BUILDING FOR

**Business:** Morph IQ Technologies — a document scanning and digital archiving service targeting UK letting agencies and property management companies.

**The operator (Filip):** Non-technical founder who builds through AI tools (Claude + Cursor). Thinks in systems and workflows, not code. Needs clear, step-by-step guidance. Existing system is Python + HTML on Windows.

**The end users (letting agency staff):** Non-technical office workers who need to quickly find documents, check compliance expiry dates, and share access with landlords or contractors. They will never touch a terminal. Everything must work through a browser.

---

## 2. WHAT ALREADY EXISTS

A fully working local document processing pipeline runs on Windows at `C:\ScanSystem_v2`. This pipeline will remain local and separate from the portal. After documents are processed and verified locally, they get imported to the portal.

### Existing Pipeline (DO NOT REBUILD — import from)

**ScanStation** (scan_station.html) — browser-based capture app. Phone camera via Camo or file browse. Captures images to client `raw/` folder.

**Auto Watcher** (auto_ocr_watch.py) — Python script polling `raw/` every 2s. Processes images through ImageMagick preprocessing → OCRmyPDF + Tesseract → searchable PDF. Creates DOC-XXXXX folders with `document.pdf`, raw image, and `review.json`.

**ReviewStation** (review_station.html) — browser-based verification app. Operator reads the PDF, fills in key fields per document type template, marks Verified/Needs Review/Failed.

**Export** (export_client.py) — Collects all Verified documents. Creates organised delivery folder: property → doc type subfolders, Excel index spreadsheet, `archive_data.json`, and `viewer.html` with embedded data.

**Server** (server.py) — Flask API on port 8765 with 21 endpoints for the local apps.

**Viewer** (viewer.html) — Offline archive browser. Loads `archive_data.json` (embedded or fetched). Properties sidebar, document list by category, PDF preview with PDF.js, field details, full-text search with highlighting.

### Existing Data Structures

**Document Unit** — each `DOC-XXXXX` folder contains:
- `document.pdf` (searchable, OCR-processed)
- Raw image (.jpg/.jpeg/.png/.tiff/.bmp)
- `review.json` (status, fields, review metadata)

**review.json structure:**
```json
{
  "doc_id": "DOC-00001",
  "doc_type": "Tenancy Agreement",
  "doc_type_template": "Tenancy Agreement",
  "doc_name": "42 Oak Road - Tenancy Agreement 1",
  "status": "Verified",
  "quality_score": "",
  "files": {
    "pdf": "document.pdf",
    "raw_image": "capture_001.jpeg"
  },
  "fields": {
    "property_address": "42 Oak Road, Harlow",
    "tenant_full_name": "John Smith",
    "landlord_name": "ABC Properties Ltd",
    "start_date": "01/01/2025",
    "end_date": "31/12/2025",
    "monthly_rent_amount": "£1,200",
    "deposit_amount": "£1,200",
    "agreement_date": "28/12/2024"
  },
  "review": {
    "reviewed_by": "Filip",
    "reviewed_at": "2026-02-21T14:32:00",
    "exported_at": "2026-02-21T15:00:00",
    "scanned_at": "2026-02-21T14:20:00",
    "notes": ""
  }
}
```

**archive_data.json structure (output of export):**
```json
{
  "client_name": "Belvoir Harlow",
  "generated_date": "2026-02-21",
  "version": "1.0",
  "total_documents": 47,
  "properties": {
    "42 Oak Road, Harlow": {
      "Tenancy Agreements": [
        {
          "doc_id": "DOC-00001",
          "doc_name": "42 Oak Road - Tenancy Agreement 1",
          "doc_type": "Tenancy Agreement",
          "filename": "42 Oak Road - Tenancy Agreement.pdf",
          "pdf_path": "42 Oak Road, Harlow/Tenancy Agreements/42 Oak Road - Tenancy Agreement.pdf",
          "fields": { ... },
          "full_text": "This tenancy agreement is made between...",
          "quality_score": "",
          "ocr_confidence": null
        }
      ],
      "Gas Safety Certificates": [ ... ]
    }
  }
}
```

### 5 Document Type Templates

| Document Type | Verified Fields |
|---|---|
| **Tenancy Agreement** | property_address, tenant_full_name, landlord_name, start_date, end_date, monthly_rent_amount, deposit_amount, agreement_date |
| **Gas Safety Certificate** | property_address, landlord_name, engineer_name, gas_safe_reg, inspection_date, expiry_date, appliances_tested, result, defects_noted |
| **EICR** | property_address, electrician_name, company_name, registration_number, inspection_date, next_inspection_date, overall_result, observations |
| **EPC** | property_address, current_rating, potential_rating, date_of_assessment, valid_until, assessor_name, certificate_number |
| **General Document** | document_title, ocr_quality, searchable, notes |

**Planned but not yet built:** Deposit Protection Certificate, Inventory/Check-in Report.

---

## 3. WHAT WE'RE BUILDING

A hosted web application (the "portal") that lets Morph IQ's clients log in and access their digitised document archive through a browser. This replaces the current offline viewer.html delivery with a persistent, searchable, always-available web application.

### Architecture Decision: Python-first (Flask)

**Why:** The entire existing system is Python. The operator builds through AI tools and already understands Flask (server.py is Flask). Minimum learning curve, maximum code reuse from the existing viewer and export logic.

**Stack:**
- **Backend:** Python 3.12+, Flask, Gunicorn (production)
- **Database:** PostgreSQL (full-text search built-in, robust, free)
- **ORM:** SQLAlchemy with Flask-SQLAlchemy
- **Auth:** Flask-Login + Werkzeug password hashing (no external auth service needed at this scale)
- **File storage:** Local filesystem initially → S3-compatible when scaling
- **Frontend:** Server-rendered HTML templates (Jinja2) + vanilla JavaScript. No React, no build tools. Keep it simple.
- **CSS:** Tailwind via CDN (consistent with current site aesthetic)
- **PDF viewing:** PDF.js (already used in viewer.html)
- **AI Chat:** Claude API (Anthropic SDK for Python)
- **Hosting:** DigitalOcean Droplet ($6-12/month) or Railway
- **Domain:** morphiq.co.uk (already purchased)

### System Topology

```
┌─────────────────────────────────────────────────────────┐
│                     CLIENTS (Browser)                    │
│              https://portal.morphiq.co.uk                │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS (Nginx reverse proxy)
┌──────────────────────▼──────────────────────────────────┐
│                  PORTAL SERVER (Linux VPS)                │
│                                                          │
│  Flask App (Gunicorn)                                    │
│  ├── Auth (login, sessions, roles)                       │
│  ├── Dashboard (stats, recent docs, alerts)              │
│  ├── Documents (browse, filter, view PDF, field details) │
│  ├── Search (full-text via PostgreSQL ts_vector)         │
│  ├── Compliance (expiry tracking, status, alerts)        │
│  ├── AI Chat (Claude API, document-grounded Q&A)         │
│  ├── Request Scan (submit new scanning jobs)             │
│  └── Admin (import, user management)                     │
│                                                          │
│  PostgreSQL Database                                     │
│  ├── users, organisations, roles                         │
│  ├── properties, documents, fields                       │
│  ├── compliance_events (expiry tracking)                 │
│  ├── scan_requests                                       │
│  └── audit_log                                           │
│                                                          │
│  File Storage                                            │
│  └── /data/storage/{org_id}/{doc_id}/                    │
│      ├── document.pdf                                    │
│      └── original.jpeg                                   │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────▼─────────────┐
         │  IMPORT BRIDGE (script)    │
         │                            │
         │  Reads local export output │
         │  (archive_data.json +      │
         │   PDF files)               │
         │  Pushes to portal DB +     │
         │  file storage via API      │
         └─────────────┬─────────────┘
                       │
         ┌─────────────▼─────────────┐
         │  LOCAL SCANNING STATION    │
         │  (Windows, unchanged)      │
         │                            │
         │  ScanStation → Watcher →   │
         │  ReviewStation → Export    │
         └───────────────────────────┘
```

### The Import Bridge

The key connector between existing system and portal. After Filip exports a client delivery locally, he runs the import script which:

1. Reads `archive_data.json` from the export folder
2. For each document: creates/updates the DB record, uploads the PDF to portal file storage
3. Calculates compliance events (extracts expiry dates, flags upcoming/overdue)
4. Returns a summary of what was imported

This means the local pipeline stays exactly as-is. No changes needed.

---

## 4. DATABASE SCHEMA

```sql
-- Organisations (each letting agency is one org)
CREATE TABLE organisations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    address TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Users (agency staff, Filip as admin, shared access users)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
        -- 'admin' = Filip/Morph IQ staff (sees all orgs)
        -- 'manager' = agency owner/manager (full access to their org)
        -- 'staff' = agency employee (view + search, no export)
        -- 'viewer' = read-only shared access (landlord, contractor)
    org_id INTEGER REFERENCES organisations(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Properties (normalised from document field data)
CREATE TABLE properties (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organisations(id),
    address VARCHAR(500) NOT NULL,
    postcode VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(org_id, address)
);

-- Documents (core entity — one row per verified document)
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organisations(id),
    property_id INTEGER REFERENCES properties(id),
    doc_id VARCHAR(20) NOT NULL,           -- e.g. DOC-00001 (from local system)
    doc_name VARCHAR(500),
    doc_type VARCHAR(100) NOT NULL,         -- e.g. "Tenancy Agreement"
    status VARCHAR(50) DEFAULT 'active',    -- active, archived, superseded
    pdf_path VARCHAR(500) NOT NULL,         -- relative path in file storage
    original_image_path VARCHAR(500),
    full_text TEXT,                          -- OCR text for search
    full_text_search TSVECTOR,              -- PostgreSQL full-text search vector
    quality_score VARCHAR(20),
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    scanned_at TIMESTAMP,
    exported_at TIMESTAMP,
    imported_at TIMESTAMP DEFAULT NOW(),
    batch_date DATE,
    UNIQUE(org_id, doc_id)
);

-- Trigger to auto-update search vector
CREATE INDEX idx_documents_fts ON documents USING GIN(full_text_search);

CREATE OR REPLACE FUNCTION documents_search_update() RETURNS TRIGGER AS $$
BEGIN
    NEW.full_text_search := to_tsvector('english', COALESCE(NEW.full_text, '') || ' ' || COALESCE(NEW.doc_name, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_documents_search
    BEFORE INSERT OR UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION documents_search_update();

-- Document fields (key-value pairs per document, variable by type)
CREATE TABLE document_fields (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,       -- e.g. "tenant_full_name"
    field_value TEXT,
    field_label VARCHAR(200),               -- e.g. "Tenant Full Name" (display)
    UNIQUE(document_id, field_name)
);

CREATE INDEX idx_fields_document ON document_fields(document_id);
CREATE INDEX idx_fields_name_value ON document_fields(field_name, field_value);

-- Compliance events (derived from document fields with dates)
CREATE TABLE compliance_events (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organisations(id),
    property_id INTEGER REFERENCES properties(id),
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,       -- 'gas_safety_expiry', 'eicr_due', 'epc_expiry', 'tenancy_end'
    event_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'upcoming',  -- 'expired', 'expiring_soon', 'upcoming', 'valid'
    description TEXT,
    notified_at TIMESTAMP,                  -- when alert was sent (future feature)
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_compliance_org_date ON compliance_events(org_id, event_date);
CREATE INDEX idx_compliance_status ON compliance_events(status);

-- Scan requests (client submits via portal)
CREATE TABLE scan_requests (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organisations(id),
    requested_by INTEGER REFERENCES users(id),
    description TEXT NOT NULL,
    document_count_estimate INTEGER,
    status VARCHAR(50) DEFAULT 'pending',   -- pending, scheduled, in_progress, complete
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- AI chat history (per user, per org)
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organisations(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    role VARCHAR(20) NOT NULL,              -- 'user' or 'assistant'
    content TEXT NOT NULL,
    documents_referenced TEXT,              -- JSON array of doc_ids used in context
    created_at TIMESTAMP DEFAULT NOW()
);

-- Audit log (every action tracked for GDPR)
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    org_id INTEGER REFERENCES organisations(id),
    action VARCHAR(100) NOT NULL,           -- 'login', 'view_document', 'search', 'export', 'ai_chat'
    detail TEXT,                             -- JSON with specifics
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_org_date ON audit_log(org_id, created_at);
```

---

## 5. PORTAL PAGES & ROUTES

### Authentication
| Route | Method | Description |
|---|---|---|
| `/login` | GET/POST | Login page. Email + password. Redirect to dashboard on success. |
| `/logout` | GET | Clear session, redirect to login. |
| `/forgot-password` | GET/POST | Password reset request (email link). |

### Main Portal (all require login)
| Route | Method | Description |
|---|---|---|
| `/` | GET | Dashboard. Stats cards (total docs, properties, expiring soon, recent). Quick actions. |
| `/documents` | GET | Document browser. Filter by property, doc type, date range, status. Paginated table. |
| `/documents/<id>` | GET | Single document view. PDF preview (PDF.js) + field details + metadata. |
| `/search` | GET | Full-text search. Query → PostgreSQL `ts_query`. Results with snippets and highlighting. |
| `/compliance` | GET | Compliance dashboard. Three sections: Expired (red), Expiring within 30 days (amber), Valid (green). Grouped by property. |
| `/ai-chat` | GET | AI assistant. Chat interface. Queries grounded in org's documents via Claude API. |
| `/request-scan` | GET/POST | Submit a new scanning request. Description, estimated count, notes. |
| `/settings` | GET/POST | User profile, password change. Org settings for managers. |

### Admin (role: admin only)
| Route | Method | Description |
|---|---|---|
| `/admin/import` | GET/POST | Upload archive_data.json + PDF zip → import to portal. |
| `/admin/orgs` | GET | List all organisations. |
| `/admin/orgs/<id>/users` | GET/POST | Manage users for an org. Add/remove/change roles. |

### API (for frontend JS calls)
| Route | Method | Description |
|---|---|---|
| `/api/documents` | GET | JSON document list with filters. For AJAX table refresh. |
| `/api/search` | GET | JSON search results. `?q=query&page=1` |
| `/api/compliance/summary` | GET | JSON compliance counts and upcoming events. |
| `/api/chat` | POST | Send message, receive AI response. `{ message: "..." }` |
| `/api/pdf/<doc_id>` | GET | Serve PDF file. Auth-checked. |

---

## 6. PAGE DESIGNS

The portal UI should match the aesthetic established on the Morph IQ website: clean white backgrounds, brand blue (#0B53CC) as primary colour, the stacked document logo mark, Sora font for headings, Inter for body text. Dark sidebar navigation in the portal.

### Dashboard (`/`)
- Top bar: org name, user name, logout
- Sidebar: Dashboard, Documents, Search, Compliance, AI Assistant, Request Scan, Settings
- Main area:
  - 4 stat cards: Total Documents, Properties, Expiring Soon (count, red if >0), Last Import Date
  - Compliance summary bar (X expired, Y expiring in 30 days, Z valid) — links to compliance page
  - Recent documents table (last 10 imported)
  - Quick actions: "Search documents", "View compliance", "Ask AI"

### Documents (`/documents`)
- Filter bar: Property dropdown, Doc Type dropdown, Date range, Status
- Paginated table: Document Name, Property, Type, Key Date (expiry or end date), Status, Actions (View)
- Click row → document detail page

### Document Detail (`/documents/<id>`)
- Left: PDF viewer (PDF.js, full page, zoom controls, page navigation)
- Right: Field details panel (all verified fields displayed as label: value pairs), metadata (scanned, reviewed, imported dates, reviewer)
- Top: document name, type badge, property, back button

### Search (`/search`)
- Search bar (prominent, top of page)
- Results: document name, property, type, snippet with highlighted matches
- Click result → document detail page

### Compliance (`/compliance`)
- Three sections with counts:
  - 🔴 Expired (past due) — table of expired docs with property, type, expiry date, days overdue
  - 🟡 Expiring Soon (next 30 days) — same table format
  - 🟢 Valid — count only, expandable
- Filter by property
- Each row links to the document

### AI Chat (`/ai-chat`)
- Chat interface (messages list, input at bottom)
- Suggested prompts: "What's expiring soon?", "Show me everything for [property]", "Give me a portfolio summary", "List all tenants and rent amounts"
- Backend: collects relevant documents for the org, sends to Claude API with the user's question as context
- Responses reference specific documents and fields

### Request Scan (`/request-scan`)
- Simple form: description of what needs scanning, estimated number of docs, any special notes
- History of past requests with status

---

## 7. IMPORT BRIDGE SPECIFICATION

The import script runs on Filip's local machine after an export. It reads the export output and pushes to the portal.

### Input
The script reads from a local export delivery folder:
- `archive_data.json` — all document metadata, fields, full text, organised by property
- PDF files in property/doc-type subfolders

### Process
```
1. Read archive_data.json
2. Authenticate with portal API (admin API key)
3. For each property in archive_data.properties:
   a. Create/find property record in portal DB
   b. For each document category → for each document:
      i.   Create/update document record (doc_id is the unique key per org)
      ii.  Insert/update all fields in document_fields table
      iii. Upload PDF to portal file storage
      iv.  Extract compliance events:
           - Gas Safety: expiry_date → gas_safety_expiry
           - EICR: next_inspection_date → eicr_due
           - EPC: valid_until → epc_expiry
           - Tenancy: end_date → tenancy_end
      v.   Calculate compliance status:
           - Past today → 'expired'
           - Within 30 days → 'expiring_soon'
           - Otherwise → 'valid'
4. Return import summary (new docs, updated docs, compliance events created)
```

### Portal Import API Endpoints
| Route | Method | Description |
|---|---|---|
| `/api/admin/import` | POST | Accepts multipart: `archive_data` (JSON) + `pdfs` (zip file). Requires admin API key header. |
| `/api/admin/import/status/<job_id>` | GET | Check import progress. |

---

## 8. AI CHAT IMPLEMENTATION

### How It Works
1. User sends a message via `/api/chat`
2. Backend queries the org's documents to build context:
   - If the message mentions a property → filter docs for that property
   - If the message mentions a doc type → filter by type
   - If the message asks about expiry/compliance → include compliance_events
   - For general queries → include a summary of all properties and doc counts + recent compliance data
3. Build a Claude API prompt with the document context + user's question
4. Send to Claude API (model: claude-sonnet-4-5-20250929 for speed/cost balance)
5. Return the response to the user
6. Store both messages in chat_messages table

### Claude API System Prompt (for document chat)
```
You are the Morph IQ document assistant for {org_name}. You answer questions about the organisation's digitised property documents.

You have access to the following document data:
{document_context}

Rules:
- Only answer based on the documents provided. If you don't have the information, say so.
- Reference specific documents by name and property when answering.
- For compliance questions, always mention specific dates and how many days until/since expiry.
- Keep answers concise and practical. These are busy letting agency staff.
- If asked to do something you can't (edit documents, send emails), explain what you can do instead.
```

---

## 9. BUILD SEQUENCE

Build in this exact order. Each phase produces a working, testable increment.

### Phase 1: Foundation (Day 1-2)
- [ ] Project structure (Flask app factory pattern)
- [ ] PostgreSQL database + SQLAlchemy models
- [ ] Database migrations (Flask-Migrate / Alembic)
- [ ] User authentication (login, logout, session management)
- [ ] Role-based access control middleware
- [ ] Base HTML template with sidebar navigation

### Phase 2: Core Portal (Day 3-5)
- [ ] Dashboard page with stat cards (hardcoded data initially)
- [ ] Documents list page with filters and pagination
- [ ] Document detail page with PDF viewer (PDF.js) and fields panel
- [ ] Properties derived from document data
- [ ] Compliance dashboard (3-section layout with status calculation)

### Phase 3: Import Bridge (Day 5-6)
- [ ] Import API endpoint (accepts archive_data.json + PDF zip)
- [ ] Import script (local Python script that calls portal API)
- [ ] Compliance event extraction from imported fields
- [ ] Test with a real export from the local system

### Phase 4: Search (Day 7)
- [ ] PostgreSQL full-text search setup (tsvector, gin index)
- [ ] Search page with results and snippets
- [ ] Search highlighting in results
- [ ] Search from document full_text + doc_name + field values

### Phase 5: AI Chat (Day 8-9)
- [ ] Chat page UI
- [ ] Claude API integration (Python SDK)
- [ ] Document context builder (query relevant docs for the org)
- [ ] Chat message storage
- [ ] Suggested prompts

### Phase 6: Polish & Deploy (Day 10-12)
- [ ] Request Scan page
- [ ] Settings page (profile, password change)
- [ ] Admin: user management
- [ ] Email alerts for expiring documents (optional, can defer)
- [ ] Nginx + Gunicorn + SSL setup on VPS
- [ ] DNS: portal.morphiq.co.uk → VPS

---

## 10. PROJECT STRUCTURE

```
morph-iq-portal/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── config.py                # Config (dev, prod, test)
│   ├── extensions.py            # db, login_manager, migrate
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py              # User, Organisation
│   │   ├── document.py          # Document, DocumentField, Property
│   │   ├── compliance.py        # ComplianceEvent
│   │   └── chat.py              # ChatMessage
│   ├── auth/
│   │   ├── __init__.py          # Blueprint
│   │   ├── routes.py            # login, logout, forgot-password
│   │   └── forms.py             # WTForms
│   ├── portal/
│   │   ├── __init__.py          # Blueprint
│   │   ├── routes.py            # dashboard, documents, compliance, search, chat, request-scan
│   │   └── services.py          # Business logic (compliance calc, search, AI chat)
│   ├── admin/
│   │   ├── __init__.py          # Blueprint
│   │   ├── routes.py            # import, user management
│   │   └── import_service.py    # archive_data.json parser + DB writer
│   ├── api/
│   │   ├── __init__.py          # Blueprint
│   │   └── routes.py            # JSON API endpoints
│   ├── templates/
│   │   ├── base.html            # Base layout with sidebar
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── forgot_password.html
│   │   ├── portal/
│   │   │   ├── dashboard.html
│   │   │   ├── documents.html
│   │   │   ├── document_detail.html
│   │   │   ├── search.html
│   │   │   ├── compliance.html
│   │   │   ├── ai_chat.html
│   │   │   └── request_scan.html
│   │   └── admin/
│   │       ├── import.html
│   │       └── users.html
│   └── static/
│       ├── css/
│       │   └── portal.css       # Custom styles beyond Tailwind
│       ├── js/
│       │   ├── pdf-viewer.js    # PDF.js integration
│       │   ├── search.js        # Search UI logic
│       │   └── chat.js          # Chat interface
│       └── img/
│           └── logo.png
├── migrations/                   # Alembic migrations
├── scripts/
│   └── import_to_portal.py      # Local import bridge script
├── requirements.txt
├── .env.example
├── gunicorn.conf.py
├── Dockerfile                    # Optional, for containerised deploy
└── README.md
```

---

## 11. KEY CONFIGURATION

### .env.example
```
FLASK_APP=app
FLASK_ENV=development
SECRET_KEY=change-this-to-a-random-string
DATABASE_URL=postgresql://morph:password@localhost:5432/morphiq
STORAGE_PATH=/data/storage
ANTHROPIC_API_KEY=sk-ant-...
ADMIN_API_KEY=change-this-for-import-auth
```

### requirements.txt
```
flask>=3.0
flask-sqlalchemy>=3.1
flask-migrate>=4.0
flask-login>=0.6
flask-wtf>=1.2
psycopg2-binary>=2.9
gunicorn>=22.0
python-dotenv>=1.0
anthropic>=0.40
werkzeug>=3.0
```

---

## 12. DESIGN TOKENS (from website)

```css
:root {
  --brand-blue: #0B53CC;
  --brand-blue-light: #3D7BF5;
  --brand-blue-dark: #0A1628;
  --sidebar-bg: #0F172A;
  --sidebar-text: rgba(255,255,255,0.6);
  --sidebar-active: #ffffff;
  --bg-primary: #ffffff;
  --bg-secondary: #F8FAFC;
  --text-primary: #0A1628;
  --text-secondary: rgba(10,22,40,0.55);
  --border: rgba(10,22,40,0.08);
  --success: #059669;
  --warning: #D97706;
  --danger: #DC2626;
  --font-heading: 'Sora', sans-serif;
  --font-body: 'Inter', sans-serif;
}
```

---

## 13. CONSTRAINTS & RULES

1. **GDPR compliance from day one.** Every document access is logged in audit_log. Users only see their own org's data. No cross-org data leakage ever.
2. **The local scanning pipeline is never modified by this project.** The portal imports from its output — that's the only connection.
3. **No JavaScript frameworks.** Vanilla JS + Jinja2 templates. The operator needs to be able to understand and modify the code with AI assistance.
4. **PostgreSQL only.** No SQLite, no MySQL. Full-text search and robust concurrent access matter.
5. **Mobile-responsive.** Letting agents check documents on phones. The portal must work on mobile screens.
6. **PDF files are served through the app** (not direct filesystem links). This ensures auth checking on every access.
7. **Compliance status is recalculated on every page load** for the compliance dashboard (or cached with a short TTL). Dates change daily.
8. **AI chat context window management.** Don't send every document to Claude. Select the most relevant ones based on the query. Max ~50 document summaries or ~10 full documents per query.

---

## 14. TESTING WITH REAL DATA

After Phase 3, test the full loop:

1. On the local Windows machine, process 10-20 test documents through ScanStation → ReviewStation → Export
2. Run the import bridge script pointing at the export folder
3. Log in to the portal and verify:
   - All documents appear with correct fields
   - PDFs load and are viewable
   - Search finds documents by text content and field values
   - Compliance dashboard shows correct expiry statuses
   - Different user roles see appropriate content

---

## 15. FUTURE FEATURES (not in this build, but designed for)

The database schema and architecture deliberately support these future features without schema changes:

- **Email alerts for expiring documents** — compliance_events table has notified_at column; a cron job checks for upcoming events and sends emails
- **Shared access links** — users table with role='viewer' and org assignment; no schema change needed
- **Multiple scanning stations** — import bridge works from any machine that can reach the portal API
- **Document versioning** — documents table status='superseded' allows keeping history while showing current
- **Custom document type templates** — document_fields table is fully flexible; any field name/value pair works
- **White-label for multiple operators** — organisations table already isolates everything by org_id

---

## 16. INSTRUCTIONS FOR THE AI BUILDING THIS

You are building the Morph IQ client portal from scratch. This specification is your complete reference.

**Your approach:**
1. Start with Phase 1 (foundation). Get the Flask app running with auth before anything else.
2. Build one phase at a time. Each phase must be working and testable before moving to the next.
3. Show the full code for each file. Don't use placeholders or "..." — the operator will paste your code directly.
4. After each phase, tell the operator exactly how to test it (specific URLs to visit, what they should see).
5. When you write database models, also write the migration. When you write routes, also write the templates.
6. Use clear, readable code with comments. The operator learns from reading the code.

**Don't:**
- Don't add features not in this spec. Build exactly what's described.
- Don't use TypeScript, React, Next.js, or any JS framework. Vanilla JS + Jinja2.
- Don't use SQLite. PostgreSQL only.
- Don't skip error handling. Every route should handle failures gracefully.
- Don't build the local scanning pipeline. It already exists and works.

**Start by:** Creating the project structure from Section 10, the database models from Section 4, and the auth system. Then present the operator with a working login page they can see in their browser.
