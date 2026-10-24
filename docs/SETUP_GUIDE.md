# Setup Guide

Two ways to run MorphIQ:

- **Demo portal** (5 minutes, no OCR tools or API key needed): synthetic data for one fictional letting agency.
- **Full system**: ScanStation capture, the OCR and AI pipeline, ReviewStation and the portal.

All commands run from the repository root.

---

## 1. Install Python packages

Python 3.11 or newer.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

---

## 2. Demo portal

```bash
python scripts/seed_demo_data.py
```

This writes `demo/portal.db` and a `demo/Clients/` folder of generated certificate PDFs, then prints the login emails and a one-off password. Everything in it is synthetic.

Start the portal against the demo data:

```bash
# macOS / Linux
export DATABASE_URL=demo/portal.db MORPHIQ_CLIENTS_DIR=demo/Clients
export PORTAL_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
export GEMINI_API_KEY=demo-placeholder
python portal_new/app.py
```

```bat
:: Windows (Command Prompt)
set DATABASE_URL=demo\portal.db
set MORPHIQ_CLIENTS_DIR=demo\Clients
for /f %i in ('python -c "import secrets; print(secrets.token_urlsafe(48))"') do set PORTAL_SECRET_KEY=%i
set GEMINI_API_KEY=demo-placeholder
python portal_new\app.py
```

Open http://127.0.0.1:5000 and sign in as `manager@morphiq-demo.test` (agency view) or `admin@morphiq-demo.test` (platform view). Ask AI needs a real Gemini key; everything else works with the placeholder.

---

## 3. Full system

### System tools

| Tool | Used for | Windows install |
|---|---|---|
| Tesseract OCR | Text recognition | https://github.com/UB-Mannheim/tesseract/wiki (tick "Add to PATH") |
| OCRmyPDF | Searchable PDFs | installed by `pip install ocrmypdf` |
| ImageMagick | Image clean-up before OCR | https://imagemagick.org (tick "Add to PATH") |

Run `setup_check.bat` on Windows to confirm everything is found.

### Configuration

```bash
copy .env.example .env      # cp on macOS/Linux
```

Fill in `GEMINI_API_KEY` and a strong `PORTAL_SECRET_KEY` (the portal refuses to start with a weak one).

### Database and first admin

```bash
python scripts/init_portal_db.py      # creates the core tables in portal.db
python portal_new/seed_admin.py       # creates the first admin user (prompts for details)
```

Both are safe to re-run.

### Run it

On Windows, `Start_System_v2.bat` starts the document watcher, the ScanStation API server (http://127.0.0.1:8765) and opens ScanStation. Start the portal with `python portal_new/app.py`. `Stop_System.bat` stops the watcher and API server.

The flow:

1. **ScanStation**: capture with a camera or upload files for a client.
2. **Watcher** (`auto_ocr_watch.py`): cleans up images, runs OCR, then Gemini classifies the document and extracts its fields.
3. **ReviewStation**: a person checks the extracted fields against the document and marks it Verified, Needs Review or Failed.
4. **Portal**: verified documents sync into `portal.db` and appear for that agency, with compliance status worked out from their expiry dates.

Pipeline logs are in `Clients/<client>/Logs/pipeline.log`.

---

## 4. Tests and evaluation

```bash
pytest -q                                   # unit and integration tests
python eval/golden/generate_golden.py       # build the synthetic evaluation set
python -m eval.run_eval                     # offline evaluation against quality thresholds
npm install && npx playwright install chromium && npm run test:smoke   # browser smoke test
python scripts/scan_tracked_secrets.py      # check tracked files for secrets
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `PORTAL_SECRET_KEY is weak or a placeholder` | Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `no such table: clients` | Run `python scripts/init_portal_db.py` against the same `DATABASE_URL`. |
| Documents never leave `raw/` | Check the watcher is running and read `Clients/<client>/Logs/pipeline.log`. |
| OCR step fails | Confirm `tesseract --version` and `magick --version` work in a new terminal. |
