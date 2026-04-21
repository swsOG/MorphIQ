# Contributor Handoff

> Last updated: 2026-04-21
> Purpose: fast public-safe context for engineers and collaborators joining the repo.

## Product Summary

MorphIQ is a document intelligence platform for compliance-heavy workflows. It captures documents, OCRs them, classifies them, extracts structured fields, routes them through human verification, and publishes approved records into a tenant-scoped portal.

## Core Product Flow

1. Capture a document in ScanStation.
2. Process it through OCR and AI extraction.
3. Review and verify the extracted data.
4. Publish the verified document into the portal.
5. Handle client-reported issues through a structured exception workflow.
6. Replace the live version only after corrected data is re-verified.

## Current Engineering Shape

- One shared `portal.db` powers the portal.
- Manager users are scoped to their assigned client.
- Admin users can manage broader operations.
- The portal now includes a first-class issue workflow for post-delivery corrections.
- Browser smoke coverage exists for the report-issue to admin-triage path.

## Verification Signals

- Pytest coverage exists for pipeline basics, auth boundaries, and issue flows.
- Browser smoke coverage exists via Playwright.
- `.env` and runtime database files are intentionally kept out of Git.

## Contribution Guardrails

- Keep secrets out of the repo. Use `.env` and `.env.example`.
- Treat sample/demo fixtures as synthetic.
- Prefer public-safe documentation over internal operational notes.
- Preserve tenant isolation and verification gates when changing the product.

## Important Files

- `README.md`
- `docs/PROJECT_BRAIN.md`
- `docs/SETUP_GUIDE.md`
- `portal_new/app.py`
- `auto_ocr_watch.py`
- `ai_prefill.py`
- `tests/`
