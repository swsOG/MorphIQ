# MORPH IQ — COWORK CONTEXT

> **What this is:** The ground truth for every Cowork session. Read this before doing anything.
> **Last updated:** 2026-03-21

---

## WHO I AM

I'm Filip, founder of Morph IQ Technologies — a UK-based document scanning and compliance platform for letting agencies. I build the product using AI tools (Claude, Cursor). I think in systems and workflows, not code. Give me direct, critical feedback — not validation.

---

## WHAT MORPH IQ IS

Morph IQ digitises property documents for letting agencies, extracts key compliance data using AI, and provides a client portal for document access and compliance tracking. The core value proposition is compliance intelligence — catching missed certificate expiry dates and protecting agencies from fines (up to £6,000) and legal risk.

**Tagline:** "Not just scanned — understood."

**One-line vision:** "The operating system for property document compliance."

---

## FOLDER MAP

Everything lives under `Desktop\MorphIQ\`. Two main areas:

### Product\
The working product codebase (formerly C:\ScanSystem_v2). **Do not move, rename, or restructure files here without explicit instruction.** This is a live development environment connected to Cursor IDE and git.

Key contents:
- `portal_new/` — Client-facing Flask web portal (runs on port 5000)
- `scan_station.html` — Browser-based document capture app
- `review_station.html` — Browser-based verification app for AI-extracted fields
- `server.py` — Flask API server (runs on port 8765)
- `ai_prefill.py` — Claude API integration for document classification and field extraction
- `auto_ocr_watch.py` — Watches for new scans and runs OCR pipeline automatically
- `sync_to_portal.py` — Bridges processed documents into the portal database
- `bulk_import.py` — Batch import tool for stress testing with synthetic documents
- `export_client.py` — Exports client document packs
- `portal.db` — SQLite database (the single source of truth for portal data)
- `Clients/` — Processed document files organised by client
- `Templates/` — Document type templates for field extraction
- `PROJECT_BRAIN.md` — **Authoritative technical source of truth.** Current system state, architecture, database schema, what's built, what's not. Read this for any technical question.
- `VISION.md` — End-state product vision. Describes where we're going, not where we are.
- `PROJECT_INSTRUCTIONS.md` — Session protocol for Claude AI sessions (used in claude.ai, not directly relevant to Cowork but useful context)
- `.cursorrules` — Cursor IDE configuration
- `.env` — Environment variables (API keys, etc.) **NEVER read, display, copy, or reference the contents of this file.**

### Business\
Business operations, design, legal, and planning documents.

- `Design/` — Logo files (MORPH_IQ_FINAL_LOGO.png and transparent version), website HTML draft (MorphIQ_Website_Updated.html), PDF leave-behind draft
- `Legal documents/` — Legal compliance roadmap (.docx), shareholders agreement (.docx), complete task list (.md)
- `Written Prompts/` — Prompt library (PROMPT_LIBRARY.md), AI toolkit, business prompts, software prompts
- `Building Infrastructure/` — PHASE_2_SPEC.md (scaling and infrastructure planning)
- `Drawing Prompts/` — Hand-drawn sketches and visual references for UI design
- `Old Files/` — Archived older versions of documents

### storage\
Pre-existing folder. Not part of the active project workflow.

---

## CURRENT STATE (March 2026)

### Build phase
The team is in a deliberate 1–1.5 month build window. Legal/compliance prerequisites (ICO registration, insurance, GDPR) are being handled by Sydney. Filip is building the product to demo-ready state. **This is intentional — do not push toward sales or client outreach.**

### What works
- Full pipeline operational: ScanStation → OCR → AI Prefill → ReviewStation → Sync → Portal
- Portal runs locally with property-first architecture, compliance tracking, document viewer
- AI prefill supports 6 document types with auto-detection
- Stress test in progress with 1,000 synthetic documents across 5 fictional clients

### What's missing
- Portal authentication (no login system yet — required before client demos)
- Pricing strategy not finalised
- Demo videos not at final quality
- PDF leave-behind needs polish
- Public website being redesigned by Mishek

### Five readiness criteria (ALL must be met before going to market)
1. Polished public-facing marketing website
2. Demo videos
3. PDF leave-behind / one-pager
4. Fully working client portal with authentication
5. ScanStation and ReviewStation working without bugs

---

## TEAM

| Person | Role |
|--------|------|
| **Filip** | Product builder. Software, technical decisions, product direction. |
| **Sydney** | Legal/compliance setup, building sales team. First to go full-time. |
| **Mishek** | Web design. Polishing the marketing website. |
| **Antonio** | General support across the team. |

All work full-time day jobs alongside this project.

---

## TECH STACK

- **Languages:** Python (backend), HTML/JS/CSS (frontends)
- **Framework:** Flask
- **Database:** SQLite (portal.db) — do NOT suggest migrating to PostgreSQL
- **AI:** Claude API (Sonnet model) for document classification, field extraction, and portal AI chat
- **OCR:** Tesseract, OCRmyPDF, ImageMagick
- **IDE:** Cursor (project root: Desktop\MorphIQ\Product)
- **Brand:** Dark theme (#061617 background, #7AAFA6 accent), Inter font, Morph IQ logo

---

## RULES FOR COWORK

1. **Never modify Product\ files without explicit instruction.** The product codebase is managed through Cursor. Cowork's role with Product files is reading and understanding, not editing.
2. **Never read, display, or reference the contents of .env files.**
3. **Don't suggest migrating from SQLite to PostgreSQL.** That's a future decision.
4. **Don't push toward sales or client outreach.** That's being handled by other team members.
5. **Don't build DriveStation.** It's planned but deferred until after the five readiness criteria are met.
6. **Always check against the five readiness criteria.** If a task doesn't move toward them, flag it.
7. **Be direct.** Challenge assumptions, point out flaws, offer better alternatives. No sugarcoating.
8. **Read PROJECT_BRAIN.md (in Product\) for any technical questions.** It's the authoritative source of truth for current system state.
9. **Business\ files are fair game for Cowork to create, edit, and organise.** This is where Cowork adds the most value — creating documents, organising business materials, drafting content.
10. **Keep it practical.** Filip builds with AI tools, not deep programming knowledge. Explain technical concepts clearly when needed.
