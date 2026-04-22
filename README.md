# Morph IQ

**The operating system for document compliance workflows.**

MorphIQ is a local-first document scanning and compliance platform. It takes uploaded or scanned documents, converts them into searchable PDFs, classifies them with AI, extracts structured fields, routes them through human verification, and presents approved records in a tenant-scoped portal with compliance tracking and issue handling.

---

## Architecture

```text
Capture -> OCR / AI Pipeline -> Review / Verification -> Portal / Compliance
```

- **ScanStation** handles capture and upload.
- **OCR / AI Pipeline** preprocesses files, runs OCR, and performs structured extraction.
- **ReviewStation** supports verification, correction, merge, and split workflows.
- **Portal** provides authenticated, tenant-scoped access to documents, compliance state, and issue workflows.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| OCR pipeline | Tesseract, OCRmyPDF, ImageMagick |
| AI classification & extraction | Gemini Flash |
| Backend / API | Python 3, Flask, Flask-Login |
| Database | SQLite (`portal.db`) |
| Document processing | pypdf, ReportLab, pdfminer |
| Frontend | Vanilla JS, PDF.js (no framework) |
| Testing | pytest, Playwright |

---

## Key Features

**AI Document Pipeline**
- Multiple supported document types with type-specific extraction prompts
- Completeness scoring and attention flags for low-confidence results
- Batch re-processing support

**Human-in-the-Loop Verification**
- Side-by-side extracted fields and source document review
- Verification gates for required data
- Merge and split support for multi-page documents

**Compliance Workflows**
- Certificate tracking and expiry monitoring
- Property or account-level status views
- Portal issue workflow for challenged documents and rework handling

**Tenant-Scoped Portal**
- Authenticated access with client scoping
- Document search, filter, and review flows
- Pack building and export support

---

## Setup

See **[docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)** for full instructions.

**Prerequisites**

```text
Python 3.11+
Tesseract OCR
OCRmyPDF
ImageMagick
Gemini API key (set in .env - see .env.example)
```

**Quick start (Windows)**

```bat
pip install -r requirements.txt
copy .env.example .env
REM edit .env and add your Gemini key and portal secret
Start_System_v2.bat
```

---

## Project Structure

```text
MorphIQ/Product/
|-- scan_station.html
|-- review_station.html
|-- viewer.html
|-- server.py
|-- auto_ocr_watch.py
|-- ai_prefill.py
|-- sync_to_portal.py
|-- export_client.py
|-- portal_new/
|-- Templates/
|-- Clients/                # runtime data, gitignored
|-- scripts/
|-- docs/
|-- tests/
|-- Start_System_v2.bat
|-- Stop_System.bat
`-- setup_check.bat
```

---

## Status

**Active development - pre-launch.**

The core flow is operational:

- capture
- OCR
- AI extraction
- verification
- portal delivery
- issue handling

Current emphasis is on broadening test coverage, refining internal rework workflows, and keeping the repo clean, reusable, and deployment-ready.

**Reference docs**
- [docs/DEPLOYMENT_CHECKLIST.md](docs/DEPLOYMENT_CHECKLIST.md)
- [docs/PROJECT_BRAIN.md](docs/PROJECT_BRAIN.md)
- [docs/VISION.md](docs/VISION.md)

**Testing**

```bat
python -m pytest tests -q
npm install
npm run playwright:install
npm run test:smoke
python scripts/scan_tracked_secrets.py
```

---

## Repo Hygiene

- Secrets belong in `.env`, not Git.
- Runtime databases, logs, and generated test artifacts stay out of version control.
- Sample data should stay synthetic and clearly marked as such.
- Public docs should avoid internal machine paths, operational notes, and client-specific details.
