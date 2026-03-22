# MorphIQ Portal — Setup

## What this is
Search-first document archive viewer. Connects to your existing `portal.db` SQLite database and serves a clean retrieval interface for browsing, searching, and previewing scanned documents.

## Quick Start

### 1. Copy files
Copy the entire `portal_new` folder into `C:\ScanSystem_v2\` so you have:

```
C:\ScanSystem_v2\
├── portal_new\           ← NEW (this folder)
│   ├── app.py
│   ├── import_fields.py
│   ├── templates\
│   │   └── portal.html
│   └── static\
│       ├── portal.css
│       └── portal.js
├── portal\               ← OLD (keep for reference, not used)
├── portal.db             ← YOUR DATABASE (unchanged)
├── auto_ocr_watch.py
└── ...
```

### 2. Run the portal

```
cd C:\ScanSystem_v2\portal_new
python app.py
```

### 3. Open in browser

```
http://127.0.0.1:5000
```

That's it. You should see your 8 documents in the table.

## Import verified fields (optional)

If your DOC folders contain `review.json` files with filled-in fields, run:

```
cd C:\ScanSystem_v2\portal_new
python import_fields.py
```

This reads every `review.json` under `Clients\` and populates the `document_fields` table in SQLite. Safe to run multiple times.

## Notes

- **No authentication** — the portal is open. Auth will be added when needed.
- **PDF preview** works if the PDF files still exist at the paths stored in the database.
- **Old portal** (`portal\` folder) is not used. Keep it for reference or delete it.
- **Database** is not modified by the portal app (read-only). Only `import_fields.py` writes to it.
- **Flask debug mode** is on by default. For production, set `debug=False` in `app.py`.

## Keyboard shortcuts

- **Escape** — close the document detail drawer

## Dependencies

- Python 3.x
- Flask (`pip install flask`)

No other dependencies required.
