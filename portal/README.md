# Portal Scaffold (Phase 1 + Phase 2)

This directory contains the Morph IQ hosted portal architecture scaffold and data schema baseline.

## Current scope
- Phase 1: folder/module scaffolding
- Phase 2: SQLAlchemy model definitions + SQL schema file + migration instructions

## Guardrails
- Do **not** modify the existing local scan pipeline.
- Keep compatibility with existing `DOC-XXXXX` IDs and `review.json` field extraction.
- No migration files are committed in this phase.

## Key folders
- `api/` - API route layer placeholders.
- `models/` - SQLAlchemy models and SQL schema definitions.
- `services/` - business logic/service layer placeholders.
- `importer/` - import bridge placeholders.
- `frontend/` - web UI placeholders (templates + static assets).
