# Project Brain - Public Engineering Overview

> Last updated: 2026-04-21
> Purpose: concise, repo-safe technical context for contributors.

## What MorphIQ Does

MorphIQ is a document processing and compliance platform. It ingests scans and uploads, converts them into searchable PDFs, extracts structured fields with AI, sends records through human verification, and surfaces approved data in a tenant-scoped web portal.

## Core Principles

- Verified documents are safer than raw AI output.
- Tenant isolation is non-negotiable.
- Runtime data, customer data, and secrets stay out of Git.
- Demo fixtures should stay clearly synthetic and never depend on real production data.

## System Shape

- `scan_station.html` handles capture and upload.
- `auto_ocr_watch.py` watches the raw intake folders and runs preprocessing, OCR, and AI prefill.
- `review_station.html` supports verification, correction, merge, and split workflows.
- `sync_to_portal.py` writes approved document state into `portal.db`.
- `portal_new/app.py` serves the authenticated portal and related APIs.

## Current Product Capabilities

- OCR pipeline with searchable PDF output
- AI classification and field extraction
- Human verification workflow
- Tenant-scoped portal with compliance views
- Exception workflow for post-delivery issue handling
- Pack building and export support
- Baseline automated tests in pytest and Playwright

## Current Priorities

- Broaden browser smoke coverage around issue handling and admin workflows
- Continue tightening portal scoping and auth boundaries
- Improve internal rework workflows for rescans and review correction
- Keep documentation and setup paths professional and public-safe

## Repo Hygiene Rules

- Do not commit `.env`, runtime databases, generated test artifacts, or local logs.
- Keep setup docs generic and reusable across environments.
- Avoid embedding internal operational notes, client identifiers, or local machine paths in public docs.
- Treat this file as a stable technical summary, not a work diary.
