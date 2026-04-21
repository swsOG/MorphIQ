# MorphIQ - One-Page Brief

> Purpose: public-safe product context for collaborators, reviewers, and design or engineering tools.

## One-Line Summary

MorphIQ turns messy document handling into a structured compliance workflow: capture, extract, verify, publish, and monitor.

## What It Is

MorphIQ is a document intelligence platform for teams that manage large volumes of operational or compliance documents. Users upload or scan paperwork, the platform OCRs and classifies it, extracts key structured fields, and publishes approved records into a searchable portal with workflow controls and status visibility.

## Why It Exists

Many teams still manage compliance documents across inboxes, folders, spreadsheets, and calendar reminders. MorphIQ consolidates that into one system with:

- OCR and searchable archives
- AI-assisted classification and extraction
- Human verification before publish
- Tenant-scoped portal access
- Expiry and compliance tracking
- Exception handling when a delivered document is challenged

## Product Shape

1. Capture documents from uploads or camera-assisted intake.
2. Convert them into searchable PDFs.
3. Classify and extract structured fields.
4. Verify the result in a review workflow.
5. Publish approved records into the portal.
6. Track issues, corrections, and document status over time.

## Technical Summary

- Backend: Python and Flask
- Database: SQLite
- OCR pipeline: OCRmyPDF, Tesseract, ImageMagick
- AI extraction: Gemini by default, Anthropic optional
- Frontend: Jinja templates, vanilla JavaScript, CSS
- Testing: pytest and Playwright

## Positioning

MorphIQ is built to feel operational rather than purely archival. The emphasis is on document state, verification, compliance visibility, and traceable corrections rather than simply storing files.

## Public Contribution Guidelines

- Keep documentation generic and reusable.
- Keep sample data synthetic.
- Avoid committing secrets, local environment details, or operational notes that belong in private planning systems.
