# MorphIQ Portal

The authenticated, tenant-scoped web portal: overview, properties, compliance, documents, packs, reports, issues and Ask AI.

- `app.py` serves the pages and JSON APIs (Flask, Flask-Login, SQLite).
- `schema.sql` holds the core tables; `scripts/init_portal_db.py` applies it.
- `document_config.py` defines document types, extraction fields and compliance rules.
- `compliance_engine.py` works out certificate status from extracted expiry dates.
- `ai_runtime.py` wraps the Gemini calls used by Ask AI and extraction.
- `seed_admin.py` creates the first admin user.

See [docs/SETUP_GUIDE.md](../docs/SETUP_GUIDE.md) to run it, including a demo with synthetic data.
