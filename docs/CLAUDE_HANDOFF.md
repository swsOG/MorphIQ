# Claude Handoff - MorphIQ

> Last updated: 2026-04-21
> Purpose: Fast context for any new AI collaborator. Read this first, then `docs/PROJECT_BRAIN.md`.

## North Star

MorphIQ should feel like one coherent operating system for property document processing:

1. ScanStation captures the document or image.
2. ReviewStation checks AI extraction against the source.
3. Only verified documents are published to the portal.
4. If a client spots a problem, they report that specific document.
5. MorphIQ routes the issue into review rework or re-scan rework.
6. The corrected version only becomes current after re-verification.

The product promise is:

- only verified documents reach the client
- tenant scoping is enforced inside a shared `portal.db`
- corrections are controlled, auditable, and visible

## Product Model Locked In

- One shared `portal.db`, not one database per client.
- `manager` users are restricted to their assigned `client_id`.
- `admin` users can switch client context and manage broader operations.
- General support chat exists, but document complaints create formal issue tickets.
- Challenged documents remain visible with an `Under review` state.
- Corrected documents only replace the current portal version after re-verification.

## What Was Recently Implemented

### Tenant-scoped portal hardening

- managers cannot fetch the global client list
- property/document list routes are scoped
- property/document detail and PDF routes are scoped
- upload and compliance mutation routes are scoped
- automated auth tests now cover these boundaries

### Exception workflow backend

The portal now has first-class post-delivery issue handling:

- `document_issues`
- `document_issue_messages`
- `document_issue_attachments`
- `document_versions`
- `notification_outbox`

Flows now include:

- create issue from a document
- list issues
- issue detail with timeline
- assign / reroute / status update
- linked issue/support messages
- automatic resolution after re-verification

### Portal exception UX

Client-facing:

- document page has a visible `Delivery assurance` area
- `Report a problem` is the document complaint CTA
- clients immediately see `Under Review`
- issue timeline is visible on the document page
- document page links to support
- Settings has a dedicated `Support` tab

Admin-facing:

- new top-level `Issues` workspace
- inline triage actions for assign, reroute, awaiting re-verification, open doc, and support thread

### Browser smoke harness

This repo now includes:

- `package.json`
- `playwright.config.js`
- `scripts/start_portal_smoke_server.py`
- `tests/smoke/portal.smoke.spec.js`

Current smoke path proves:

1. manager logs in
2. manager reports a document issue
3. document moves to `Under Review`
4. manager reaches Support
5. admin logs in
6. admin sees the ticket in the `Issues` workspace

## Current Trust Signals

- Python regression suite passes: `42 passed`
- auth + issue coverage is live in pytest
- browser smoke passes: `npm run test:smoke`

## What Is Still Not Done

### Product / workflow gaps

- No polished dedicated re-do workspace yet inside ScanStation / ReviewStation for re-scan and review teams.
- Client issue tracking is still document-first, not a full client issue inbox.
- Support UX is functional but still early-stage.
- Notification delivery is modeled but not fully productionized.
- Version history is stored, but comparison UX is thin.

### Technical / platform gaps

- Browser smoke coverage currently proves one path, not a full suite.
- No Hetzner/VPS deployment yet.
- No password-reset-by-email flow yet.
- Packs need more end-to-end exercise.
- Dead-weight table decisions still needed for `compliance_records` and `tenants`.

### Presentation / portfolio gaps

- README / project-summary polish still needs a stronger trust-story pass.
- Website, demo video, automations, and design system are not built out yet as one coherent portfolio layer.

## Product Ideas Already Discussed

- Build a full product ecosystem, not just a codebase:
  - product
  - portal
  - website
  - demo video
  - automations
  - design system / branding
- Keep chat general, but keep document complaints anchored to formal issues.
- Separate re-scan work from review correction work operationally.

## Open Questions

- Should clients eventually get a top-level `Issues` page?
- Should the portal show richer version history after a corrected document is re-delivered?
- How visible should SLA / turnaround expectations be to the client?
- Should support stay in `Settings` long-term, or become more prominent?
- How much queue work should stay in the portal vs move into dedicated ScanStation / ReviewStation workspaces?

## Best Next Step

If the goal is technical completion before marketing polish, the strongest next step is:

**build the dedicated internal rework experience for re-scan and review teams**

After that, the best follow-up is widening browser smoke coverage for:

- issue update messages
- admin assign / reroute flows
- support message send flow
- mobile viewport smoke

## Important Files

- `docs/CLAUDE_HANDOFF.md`
- `docs/PROJECT_BRAIN.md`
- `portal_new/app.py`
- `portal_new/templates/document_view.html`
- `portal_new/templates/issues.html`
- `portal_new/templates/settings.html`
- `portal_new/static/portal.js`
- `portal_new/static/portal.css`
- `tests/test_portal_auth.py`
- `tests/test_portal_issues.py`
- `tests/smoke/portal.smoke.spec.js`
