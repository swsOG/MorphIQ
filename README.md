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

## Running Evaluations

The `eval/` package measures the AI pipeline (detection + extraction) against a
synthetic golden dataset and gates merges on configurable quality thresholds.

```bat
make eval
:: or, on Windows without make:
python eval/golden/generate_golden.py
python -m eval.run_eval
```

`run_eval` builds the dataset if needed, runs the tasks in parallel, writes a
report to `eval/report/latest/` (open `index.html`), and exits non-zero if any
threshold gate is breached.

**Flags**

```bat
python -m eval.run_eval --only detection   :: run a single task (detection|extraction|pipeline)
python -m eval.run_eval --live             :: call the real Gemini API (needs GEMINI_API_KEY)
python -m eval.run_eval --workers 4        :: parallel worker threads
python -m eval.run_eval --no-report        :: skip writing the HTML/MD/JSON report
```

**How it works.** The golden PDFs are synthetic, so the correct answer for every
case is known. Recorded Gemini-style responses (with deterministic injected
errors) are committed in `eval/golden/manifest.json`, letting CI replay them
fully offline — no API key, identical results every run. `--live` swaps in the
real model to measure actual quality. The PDFs themselves are generated on
demand and gitignored.

**Thresholds** (override via environment variables; CI fails on breach):

| Metric | Env var | Default |
|--------|---------|---------|
| Detection accuracy | `EVAL_MIN_DETECTION_ACC` | 0.90 |
| Required-field recall | `EVAL_MIN_FIELD_RECALL` | 0.85 |
| Completeness Pearson r | `EVAL_MIN_COMPLETENESS_R` | 0.85 |
| `needs_attention` F1 | `EVAL_MIN_ATTENTION_F1` | 0.80 |

`python -m eval.ci_gate` re-applies the current env thresholds to the last
`results.json` without re-running the eval.

**Expanding the dataset.** Edit `eval/golden/generate_golden.py` (bump
`CASES_PER_TYPE`, adjust `EDGE_LAYOUT`, or add value pools), then regenerate and
commit the manifest:

```bat
python eval/golden/generate_golden.py
git add eval/golden/manifest.json
```

CI (`.github/workflows/eval.yml`) runs this offline on every PR to `main` and
nightly, uploads the HTML report as an artifact, and posts the summary as a PR
comment.

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
