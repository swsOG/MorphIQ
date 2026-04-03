# MORPH IQ — END-STATE PRODUCT VISION

> **Purpose of this document:** This describes where Morph IQ is going — the fully built product operating at scale. Use this to understand the destination, not the current state. For current state, see PROJECT_BRAIN.md. For AI session context, see MASTER_PROMPT.md.
>
> **Last updated:** 2026-03-15
> **Updated by:** Filip (Founder)
> **Changes this update:** Added Layer 1b (Digital Drive Ingestion); corrected database references to reflect current architecture (SQLite now, PostgreSQL at scale).

---

## 1. WHAT MORPH IQ BECOMES

Morph IQ is a compliance infrastructure platform for property management. At full maturity, it is not a scanning service — it is the system that letting agencies, landlords, and property managers rely on to ensure every document is captured, verified, tracked, and retrievable. The scanning is the entry point. The platform is the product.

The end-state Morph IQ handles hundreds of clients across the UK property sector and adjacent industries. It operates as a subscription SaaS platform backed by a physical document processing operation, combining local scanning stations with a cloud-hosted client portal, AI-assisted workflows, and automated compliance tracking.

**One-line vision:** "The operating system for property document compliance."

---

## 2. THE FULL PRODUCT STACK

### Layer 1 — Physical Scanning Operation

Multiple scanning stations across the service area (Essex, Hertfordshire, London corridor, and beyond). Each station consists of an overhead-mounted DSLR camera, a controlled capture surface, and the ScanStation browser application. Stations are operated by trained staff — not Filip.

Stations can be deployed on-site at client offices for large agencies, or documents are collected, scanned at a Morph IQ facility, and returned. The physical operation is standardised and repeatable — any new operator can be trained in under a day using the setup guide and workflow documentation.

**At scale:** 5–10+ active scanning stations. Dedicated scanning operators. Potential on-site installations at high-volume clients. Collection and return logistics for agencies that prefer not to have on-site equipment.

### Layer 1b — Digital Drive Ingestion

Not all documents start as paper. Many clients also have hard drives, USB sticks, and shared folders full of disorganised digital files — unsorted PDFs, scanned images, Word documents, and photos of certificates with no structure or naming convention.

A dedicated ingestion tool (working name: **DriveStation**) handles this. It is a separate application from ScanStation, purpose-built for crawling digital storage, identifying and classifying files, deduplicating, and routing them into the same processing pipeline used for scanned paper. From the portal side, clients see one unified archive — documents are indistinguishable by source.

**Key principle:** Separate ingestion front-ends, shared processing pipeline and database. Two operators scanning paper and two operators sorting drives can work simultaneously on the same client job, with all documents landing in the same client folder.

**At scale:** DriveStation is offered as an additional service alongside paper scanning. Pricing is separate (per-drive flat fee or per-document at a lower rate than paper scanning). See VISION_ADDENDUM_DRIVE_SORTING.md for full implementation details.

### Layer 2 — Intelligent Processing Pipeline

The backend processing engine handles every document from raw image to verified, structured data. At full maturity, this pipeline is heavily AI-assisted:

- **Auto-capture quality check:** The system detects blur, skew, missing pages, and poor lighting before a document enters the pipeline. Operator gets immediate feedback to re-scan.
- **AI-assisted field extraction:** Claude API (or equivalent) reads the OCR output and pre-fills all key fields per document type. Confidence scores are attached to each extracted field.
- **Human-in-the-loop verification:** A trained reviewer confirms or corrects AI-extracted fields. The AI learns from corrections over time, improving accuracy and reducing review time.
- **Auto-classification:** Documents are automatically identified by type (tenancy agreement, CP12, EICR, EPC, etc.) without the operator manually selecting. The system recognises document structure, headers, and content patterns.
- **Batch processing at speed:** Large backlog jobs (thousands of documents) are processed with minimal human intervention — AI handles 80%+ of field extraction accurately, humans verify the remaining edge cases.

**Processing speed at scale:** Target of 30–60 seconds per document end-to-end (including AI extraction + human verification of flagged fields only), compared to the current 3–4 minutes per document with full manual verification.

### Layer 3 — Client Portal (Web Platform)

The client-facing portal is the primary product experience. This is what clients pay their monthly subscription for. It is a dark-themed, professional web application branded to Morph IQ.

**What clients see and do:**

- **Dashboard:** Overview of their portfolio — total properties, total documents, compliance status at a glance, upcoming expiries, recent activity.
- **Property view:** Every managed property listed with its full document history. Click a property, see every document ever processed for it — tenancy agreements, gas certs, EICRs, EPCs, deposit certificates, inventories — all organised chronologically.
- **Document viewer:** Open any document as a searchable PDF with verified key fields displayed alongside it. Download individual documents or bulk-export.
- **Compliance tracker:** The crown jewel. A live matrix showing every property against every required certificate, with clear status indicators: valid (green), expiring soon (amber), expired (red), missing (grey). Filterable by property, document type, date range, status.
- **Expiry alerts:** Automated email and in-portal notifications when certificates approach expiry. Configurable lead times (30 days, 60 days, 90 days). Escalation if not actioned.
- **Search:** Full-text search across all documents and verified fields. "Find every tenancy agreement expiring in Q2 2027." "Show me all properties where the gas cert engineer was [name]." Instant results.
- **AI chat assistant:** A conversational interface powered by Claude API where clients ask natural language questions about their portfolio. "Which properties have overdue EICRs?" "What's the total monthly rent across my portfolio?" "Show me all tenancies signed in the last 6 months." The AI has access to all of the client's verified document data and returns accurate, sourced answers.
- **Scan requests:** Clients can request document scanning through the portal — upload photos of documents directly, or request a collection/drop-off. Status tracking for each request.
- **Audit trail:** Full history of every document — when it was scanned, who verified it, what was changed, when it was accessed. GDPR-compliant, exportable for regulatory audits.
- **User management:** Multiple user accounts per organisation with role-based access. Agency owner sees everything. Individual negotiators see only their properties. Admin roles can manage users and settings.
- **Export and reporting:** Generate compliance reports, download spreadsheets of verified data, export document packs for specific properties (useful when selling a property or changing management).

**Technical architecture:** Flask backend with SQLite during early operation, migrating to PostgreSQL as client volume grows. Role-based blueprints (auth, portal, admin, api), eight core database models, GDPR audit logging, responsive design for desktop and tablet use.

### Layer 4 — Compliance Intelligence

Beyond storing and tracking documents, the mature platform provides actionable intelligence:

- **Compliance scoring:** Each property and each client portfolio gets a compliance health score based on document coverage, expiry status, and missing certificates.
- **Regulatory updates:** When property legislation changes (e.g., new Renters Reform Act requirements, updated gas safety regulations), the platform flags which clients and properties are affected and what action is needed.
- **Benchmarking:** Anonymised data across the client base allows Morph IQ to tell agencies how their compliance compares to industry averages. "Your portfolio is 94% compliant — top quartile for agencies your size."
- **Predictive alerts:** Based on historical patterns, the system predicts when documents are likely to need renewal and prompts action before the standard expiry window.

---

## 3. DOCUMENT TYPES — FULL COVERAGE

At maturity, Morph IQ handles every standard property document type in the UK lettings sector, each with its own verified field template:

**Core property compliance documents:**
- Tenancy Agreement (AST) — property, tenant, landlord, dates, rent, deposit, terms
- Gas Safety Certificate (CP12) — property, engineer, Gas Safe number, inspection/expiry dates, appliance results, warnings
- EICR (Electrical Installation Condition Report) — property, electrician, registration, inspection/next due, result, observation codes (C1/C2/C3/FI)
- EPC (Energy Performance Certificate) — property, rating, date, assessor, recommendations
- Deposit Protection Certificate — property, tenant, amount, scheme, certificate number, protection date
- Inventory / Check-in Report — property, date, clerk, room-by-room condition
- Check-out Report — property, date, clerk, condition comparison, deductions
- Section 21 / Section 8 Notices — property, tenant, notice type, date served, expiry
- Right to Rent checks — tenant, document type, check date, expiry
- Landlord consent / licence documents
- HMO licence (where applicable)
- Fire safety risk assessment
- Legionella risk assessment
- Smoke and CO alarm compliance records

**Adjacent document types (expansion sectors):**
- Accountancy: tax returns, financial statements, VAT records, payroll documents
- Legal: contracts, correspondence, court documents
- Healthcare: patient records, compliance certificates, CQC documentation
- Construction: H&S documents, CSCS cards, method statements, RAMS
- Education: student records, Ofsted documentation, safeguarding records

---

## 4. PRICING MODEL — AT SCALE

**Subscription tiers (monthly per agency):**

- **Essentials (~£99/month):** Digital archive + searchable PDFs + verified key fields + delivery spreadsheets. For smaller agencies (under 100 properties) or those starting with digitisation.
- **Professional (~£199/month):** Everything in Essentials + full portal access + compliance dashboard + expiry alerts + AI chat assistant. For active agencies wanting live compliance management.
- **Enterprise (custom pricing):** Everything in Professional + on-site scanning station + dedicated account manager + API access + custom integrations + SLA guarantees. For large agencies and property management groups (500+ properties).

**Additional revenue streams:**
- Backlog digitisation: one-off project pricing for converting existing paper archives (quoted per job based on volume)
- Per-document processing for overflow beyond subscription allowance
- White-label portal for large firms wanting their own branding
- API access for agencies wanting to integrate document data into their existing property management software
- Training and setup fees for on-site installations

---

## 5. MARKET POSITION — AT SCALE

**Primary market:** UK letting agencies and property management companies, starting in Essex/Hertfordshire/London and expanding nationally.

**Market size context:** There are approximately 15,000–20,000 letting agencies in the UK. Even capturing 1% of this market (150–200 agencies) at an average of £150/month represents £270,000–£360,000 annual recurring revenue.

**Competitive moat at scale:**
- **Network effects:** More documents processed = better AI extraction accuracy = faster processing = lower cost per document = more competitive pricing = more clients.
- **Switching cost:** Once an agency's entire archive is in Morph IQ with verified fields and compliance tracking, migrating away is painful and risky.
- **Data intelligence:** Aggregate (anonymised) insight across hundreds of agencies creates a compliance benchmarking product that no single-agency solution can offer.
- **Operational expertise:** Years of document processing experience across thousands of document types creates institutional knowledge that's hard to replicate.

**Positioning:** Morph IQ is not competing with generic scanning companies (commodity race to the bottom) or enterprise document management platforms (too complex, too expensive for SME agencies). It sits in the gap — specialist property compliance infrastructure at a price point SME agencies can afford, with intelligence they can't build themselves.

---

## 6. TEAM — AT SCALE

- **Founder/CEO (Filip):** Strategy, product direction, key client relationships, technology decisions
- **Operations Manager:** Oversees scanning operations, staff scheduling, quality control, logistics
- **Scanning Operators (5–10):** Trained document capture staff running scanning stations
- **Review Team (2–4):** Human verification specialists, trained on document types and field accuracy
- **Sales/Account Management (2–3):** Client acquisition, onboarding, retention, upselling
- **Software/Platform (1–2):** Portal development, AI pipeline, infrastructure, integrations
- **Creative/Marketing (1):** Brand, content, social media, case studies

**Total headcount at full scale:** 12–20 people

---

## 7. TECHNOLOGY STACK — AT SCALE

**Scanning stations:** Custom ScanStation browser app + overhead DSLR cameras + calibrated lighting rigs. Standardised hardware kit that can be deployed anywhere in under an hour.

**Processing pipeline:** Python backend with ImageMagick preprocessing, Tesseract/OCRmyPDF for OCR, Claude API for AI-assisted field extraction, confidence scoring, and auto-classification. Queue-based architecture for handling high-volume batch jobs.

**Client portal:** Flask with SQLite initially, migrating to PostgreSQL at scale. Role-based access control, real-time compliance dashboards, AI chat (Claude API), full-text search (PostgreSQL full-text or Elasticsearch at scale), GDPR audit logging, responsive web design.

**Infrastructure:** Cloud-hosted (AWS/GCP/Azure), automated backups, encryption at rest and in transit, SOC 2 compliance target, 99.9% uptime SLA for enterprise clients.

**Integrations:** API connections to popular property management software (Arthur, Goodlord, Reapit, Alto, Jupix), email alert systems, potential CRM integration for sales team.

---

## 8. BRAND IDENTITY — ESTABLISHED

**Name:** Morph IQ

**Tagline:** "Not just scanned — understood."

**Visual identity:** Dark theme (#061617 background, #7AAFA6 accent), Inter typography, stacked document logo mark. Premium, professional, modern. Signals trust and intelligence — not bargain-bin scanning.

**Brand voice:** Expert, clear, calm, confident. Speaks the language of property compliance. Never salesy. Positions as the knowledgeable partner who takes a serious operational burden off the client's shoulders.

**Online presence:** Professional website, active LinkedIn presence in property management circles, case studies from established clients, thought leadership on property compliance topics, Google My Business listings in served areas.

---

## 9. KEY METRICS — AT SCALE

**Business health:**
- Monthly Recurring Revenue (MRR)
- Client retention rate (target: 95%+)
- Average revenue per client
- Client acquisition cost vs lifetime value
- Net Promoter Score

**Operational efficiency:**
- Documents processed per hour per operator
- AI extraction accuracy rate (target: 90%+ without human correction)
- Average verification time per document
- Error rate (fields corrected post-delivery)
- Backlog clearance time per client

**Compliance impact:**
- Percentage of client portfolios at full compliance
- Number of expiry alerts sent vs actioned
- Reduction in client compliance incidents after onboarding

---

## 10. EXIT / LONG-TERM OPTIONS

At full maturity, Morph IQ has several strategic options:

- **Continue operating:** Profitable, growing business providing stable income and employment
- **Franchise model:** License the system, brand, and methodology to operators in other regions
- **White-label/platform play:** Sell the technology platform to larger property management firms or PropTech companies
- **Acquisition target:** Attractive to PropTech companies, property management software providers, or compliance platforms looking to add document intelligence
- **International expansion:** UK model adapted for other markets with similar property compliance requirements (Spain identified as promising second market due to comparable letting regulations and paper-heavy processes)

---

## 11. THE NORTH STAR

When Morph IQ is fully realised, a letting agency manager starts their Monday morning by logging into the portal. Their dashboard shows: 3 gas safety certificates expiring this month (already flagged to their preferred engineer), 2 new tenancy agreements processed and verified over the weekend from documents they dropped off Friday, and a compliance score of 97% across their 200-property portfolio. They type into the AI chat: "Pull together the full document pack for 14 Elm Street — we're transferring that property to a new landlord." Thirty seconds later, every document for that property is compiled and ready to download.

No filing cabinets opened. No spreadsheets manually updated. No certificates forgotten. No fines risked.

That is the product.

---

*This document describes the vision for the fully built product. It is not a current-state description. For implementation status and immediate priorities, see PROJECT_BRAIN.md. For AI session context, see PROJECT_INSTRUCTIONS.md.*
