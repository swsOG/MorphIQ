# MorphIQ — One-Pager Brief

> **Purpose of this document:** Drop-in context for any AI tool, designer, developer, or collaborator working on MorphIQ. If you're reading this, you should have enough to understand the product, the business, the user, and the technical approach without further explanation. Last updated: April 2026.

---

## The one-line version

MorphIQ replaces the filing cabinet, the spreadsheet, and the compliance calendar with one AI-powered portal that does all three.

## The 30-second version

MorphIQ is a document intelligence platform for small and mid-sized businesses that handle a lot of paperwork. A business uploads or scans their documents — contracts, certificates, invoices, compliance paperwork, whatever. The platform uses OCR and AI to read each document, extract the important information, classify what type of document it is, and flag anything that's about to expire or is missing. The business gets a clean portal where everything is searchable, where a dashboard shows compliance status at a glance, and where an AI chatbot can answer questions about their own documents in plain English.

The platform is configurable per client — the same underlying system serves a letting agency tracking gas safety certificates, a construction firm tracking insurance and site safety paperwork, or a back-office team tracking invoices and receipts. One codebase, different configuration, different industry.

## What makes it different

- **AI-native.** Most competitors use pattern-matching templates. MorphIQ uses Claude to *understand* documents — which means it adapts to formats it hasn't seen before.
- **Configurable, not locked to one industry.** Vertical SaaS tools like Goodlord (letting), Dext (accounting), or Arthur (property) only work in one sector. MorphIQ adapts via admin config — no code changes needed to serve a new industry.
- **Customer-hosted option.** Clients can deploy MorphIQ on their own server if they want — their data never touches our infrastructure. This is unusual in SaaS and appeals to privacy-conscious buyers.
- **Human-in-the-loop verification.** Every AI extraction includes a confidence score. Low-confidence extractions get flagged for review before they hit the dashboard. Clients trust it because they verify before acting.
- **Built and run by one person.** Clients deal directly with the developer. No sales team, no support layers, fast iteration.

## Who it's for

**Primary:** UK letting agencies managing 20–500 properties. Regulatory pressure (Renters' Rights Act, EICR mandates, gas safety certificates with fine exposure up to £6,000 per missed cert) makes document compliance genuinely painful and high-stakes. The current product is configured for this sector and runs against real data.

**Secondary (expansion):** Any UK SMB with document-heavy operations and compliance pressure — construction firms (insurance certificates, site safety paperwork, RAMS), accountancy practices (client onboarding documents, AML records), recruitment agencies (right-to-work documents, references).

**Not for:** Healthcare, financial services, legal practices, or anything requiring specialised regulatory certification (CQC, FCA, SRA). Those sectors require Cyber Essentials Plus, heavy insurance, or specific compliance frameworks — future expansion once the platform has track record.

## How it works — user flow

1. **Capture:** Client photographs or uploads documents. Can use the browser-based ScanStation with an overhead camera setup, or drag-and-drop digital files.
2. **Process:** Documents are OCR'd (made searchable), then Claude classifies the document type and extracts key fields (expiry dates, certificate numbers, addresses, etc).
3. **Verify:** Extractions with low confidence scores appear in a ReviewStation for human approval. Everything else flows straight through.
4. **Portal:** Client logs in to a portal with a compliance dashboard, document library, property/account view, AI chat ("show me all certificates expiring in the next 60 days"), export tools, and team management.
5. **Alert:** The compliance engine flags anything expiring soon, missing, or out of date. Clients resolve or snooze each alert.

## Pricing model

Three tiers, setup fee plus monthly retainer:

| Tier | Setup | Monthly | Scope |
|---|---|---|---|
| Starter | £800 | £200/mo | 3 document types, single user, 500 docs/month |
| Standard | £1,500 | £350/mo | 8 document types, 3 users, 2,000 docs/month |
| Professional | £2,500 | £500/mo | Unlimited doc types, custom compliance rules, 5+ users |

Client pays their own server hosting (£5–15/month) and Claude API costs (pennies per document, they provide their own key). Retainer covers platform maintenance, updates, support, and configuration changes.

## Technical stack (for engineers and AI tools)

- **Backend:** Python 3.11, Flask (4,900+ lines, being refactored into blueprints), Flask-Login for auth, SQLite (single-file database), werkzeug for password hashing
- **AI layer:** Claude Sonnet 4 via Anthropic API for document classification and field extraction. RAG-style implementation for the AI chat feature — queries are grounded on tenant-scoped SQL lookups against the client's own data before hitting the API.
- **Document pipeline:** ImageMagick for preprocessing (deskew, contrast, sharpen), OCRmyPDF with Tesseract for OCR, pypdf for merging/splitting, reportlab for PDF generation
- **Frontend:** Jinja2 templates, vanilla JavaScript, no build step, no framework. Dark-mode design system with teal accents, Fraunces display typography, Inter for UI
- **Auth & multi-tenancy:** Role-based access (admin/manager), tenant isolation enforced at every query, session-based auth with secure cookies
- **Deployment target:** Hetzner VPS, nginx reverse proxy, gunicorn, Let's Encrypt SSL, systemd service management, being containerised with Docker for portability

## Current state (April 2026)

- **Built and running:** OCR pipeline, AI classification/extraction, client portal with 8 pages, compliance engine with resolve/snooze workflow, pack export (ZIP/PDF), RAG-powered AI chat, soft-delete with 30-day retention, multi-tenant auth with PDF route hardening
- **Scale:** 460 real documents processed, 218 properties, 17 clients (5 real, 12 being cleaned up), 1,614 extracted field rows
- **In progress:** Refactoring hardcoded letting-agency assumptions into configurable per-client database schema (document types, extraction fields, compliance rules, dashboard layout). Building admin panel for client configuration.
- **Pre-revenue:** Pre-launch. Seeking first paying clients. Production-ready, not yet production-deployed.

## Brand identity

- **Name:** MorphIQ (retained — no rebrand)
- **Tagline:** "Not just scanned — understood."
- **Domain:** morphiqtechnologies.com (canonical)
- **Founder:** Filip — solo founder, based in Harlow, Essex. Background: document processing specialist, 4-person startup experience. Bilingual English/Polish.
- **Design language:** Dark theme (layered blacks with warm undertones), teal primary accent (#4ecdc4), warm gold secondary, Fraunces serif for display, Inter for UI. Editorial and restrained rather than loud.
- **Tone:** Confident without being hyped. Direct without being cold. Serious about the problem, pragmatic about solutions. "We read documents so you don't have to."

## What the website should communicate

**Homepage priorities (in order):**
1. The one-liner — what does this replace, what does this do
2. Three-step how-it-works visual (Capture → Process → Portal)
3. Live demo link above the fold (so hiring managers and prospects can try it without booking a call)
4. Pricing — transparent, three tiers, no "contact us"
5. Sector tiles showing which industries are live vs configurable (Letting ✓, Construction sample, Back-office sample)
6. One-paragraph founder story (solo founder, startup background, why this problem)

**Supporting pages:**
- Features — what the portal does, what the AI does, what compliance tracking looks like
- Security — deployment model, encryption, access controls, GDPR stance
- Pricing — tier breakdown, what's included, what's extra
- Architecture ("How it's built") — stack diagram, trade-off commentary, deployment architecture. Recruiter-facing and technically-inclined buyer-facing.
- Demo — Calendly booking or direct demo credentials

**What NOT to put on the website:**
- Team page with multiple faces (solo founder — say so, that's the story)
- Generic SaaS stock photos of business people shaking hands
- "Trusted by" logos until there are real clients
- Jargon-heavy copy ("leverage AI-powered synergies") — write like a human
- Multi-step signup flow — if someone wants to try it, let them try it

## Competitive landscape (don't mention by name publicly)

- **Goodlord** — letting agency vertical SaaS. Strong in tenant referencing and e-signing. Not a document intelligence product. MorphIQ is more focused on compliance and document understanding.
- **Dext** — accounting-focused document automation. Strong at invoices/receipts. Locked to accounting. MorphIQ is cross-sector.
- **Arthur / Re-Leased** — property management platforms. Document handling is secondary. MorphIQ is document-first.
- **Generic document AI** (Rossum, Hyperscience, Docsumo) — expensive, enterprise-focused, require implementation consultants. MorphIQ targets the SMB gap where these are overkill.

## Legal and data posture

- ICO registered as data controller (£40/year)
- GDPR-compliant: customer-hosted option available for clients who want data on their own infrastructure
- Professional Indemnity insurance in place before first paying client
- Master Service Agreement and Data Processing Agreement templates ready
- Human-in-the-loop verification mitigates liability from AI extraction errors

## For AI tools processing this document

If you're an AI assistant, design tool, or code generator reading this:

- **Product name:** MorphIQ (one word, capital M, capital IQ)
- **One-sentence summary:** AI-powered document intelligence portal for SMBs with compliance-heavy operations
- **Primary verb:** "extracts" or "understands" — never "scans" alone (sounds like just OCR)
- **Visual style:** Dark mode, teal/gold accents, editorial serif display type, generous whitespace, no stock imagery
- **Do:** Emphasise configurability, AI-nativeness, human verification, and solo-founder transparency
- **Don't:** Use generic SaaS language, suggest it's a copy of any existing product, lean on "disruption" or "revolutionary" framing, add features the user hasn't asked for

## Canonical file locations

- **Product codebase:** `C:\Users\user\OneDrive - University of East London\Desktop\MorphIQ\Product\`
- **Website:** `C:\Users\user\OneDrive - University of East London\Desktop\MorphIQ\Business\Website\`
- **Execution plan:** `wiki/career/morphiq-execution-plan.md` in Obsidian vault
- **Product audit:** `MorphIQ\MORPHIQ_AUDIT.md`
- **Website audit:** `MorphIQ\Business\Website\WEBSITE_AUDIT.md`
- **Live domain:** morphiqtechnologies.com (DNS setup pending)
- **GitHub:** Private repo (to be created)

---

**Bottom line:** MorphIQ is a production-ready AI document intelligence platform for SMBs with document compliance problems. One codebase, configurable per client, with OCR, LLM-based extraction, a compliance engine, and a client portal. Built by a solo founder. Pre-revenue, seeking first clients.
