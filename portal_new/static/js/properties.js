/**
 * MorphIQ /properties — split-panel property list + detail (fetch; no full reload).
 */
(function () {
    const CERT_KEYS = ["gas_safety", "eicr", "epc", "deposit"];
    const CERT_SHORT = { gas_safety: "GAS", eicr: "EICR", epc: "EPC", deposit: "DEP" };

    // Maps compliance key → the matching key in documents_by_type
    const COMP_TO_DOCTYPE = {
        gas_safety: "Gas Safety Certificate",
        eicr: "EICR",
        epc: "EPC",
        deposit: "Deposit Protection Certificate",
    };

    // Human-readable labels for the strip
    const COMP_STRIP_LABELS = {
        gas_safety: "Gas Safety",
        eicr: "EICR",
        epc: "EPC",
        deposit: "Deposit",
    };

    let allProperties = [];
    let activeFilter = "all";
    let listSearch = "";
    let selectedPropertyId = null;
    /** Compliance-strip filter: null = "all", or a CERT_KEYS value like "gas_safety" */
    let activeComplianceFilter = null;

    function withClientQuery(url) {
        let clientParam = new URLSearchParams(window.location.search).get("client");
        if (clientParam == null || !String(clientParam).trim()) {
            clientParam = (window.MORPHIQ_PORTAL && window.MORPHIQ_PORTAL.clientName) || "";
        }
        if (!String(clientParam).trim()) return url;
        const trimmed = String(clientParam).trim();
        const sep = url.includes("?") ? "&" : "?";
        return `${url}${sep}client=${encodeURIComponent(trimmed)}`;
    }

    function esc(s) {
        return String(s == null ? "" : s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function extractPostcode(address) {
        const m = String(address || "").match(/[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}/i);
        return m ? m[0].toUpperCase() : "";
    }

    function addressWithoutPostcode(address, postcode) {
        if (!postcode) return String(address || "").trim();
        return String(address || "")
            .replace(new RegExp(postcode.replace(/\s+/g, "\\s*"), "i"), "")
            .replace(/,\s*$/, "")
            .trim();
    }

    function certBadgeClass(status) {
        const s = (status || "missing").toLowerCase().replace(/\s+/g, "_");
        if (s === "expiring" || s === "expiring_soon") return "props-cert-badge--expiring-soon";
        if (s === "valid") return "props-cert-badge--valid";
        if (s === "expired") return "props-cert-badge--expired";
        return "props-cert-badge--missing";
    }

    function propertyStatusDotClass(p) {
        // Use pre-computed overall_status when available (set by enriched API).
        if (p.overall_status === "non_compliant") return "props-prop-status-dot--red";
        if (p.overall_status === "at_risk")       return "props-prop-status-dot--amber";
        if (p.overall_status === "compliant")     return "props-prop-status-dot--green";
        // Legacy fallback: derive from flat status fields.
        const hasExpiredOrMissing = CERT_KEYS.some((k) => {
            const s = (p[k] || "missing").toLowerCase();
            return s === "expired" || s === "missing";
        });
        if (hasExpiredOrMissing) return "props-prop-status-dot--red";
        const hasExpiring = CERT_KEYS.some((k) => {
            const s = (p[k] || "").toLowerCase();
            return s === "expiring_soon" || s === "expiring";
        });
        if (hasExpiring) return "props-prop-status-dot--amber";
        return "props-prop-status-dot--green";
    }

    function isUnknownType(doc) {
        const t = String(doc.doc_type || "").toLowerCase();
        const s = String(doc.doc_type_slug || "").toLowerCase();
        return t === "unknown" || s === "unknown" || (!doc.doc_type && !doc.doc_type_slug);
    }

    function docStatusBadgeHtml(doc) {
        const s = String(doc.status || "new").toLowerCase();
        if (s === "verified") {
            return `<span class="doc-card-status-badge doc-card-status-badge--verified">Verified</span>`;
        }
        if (s === "ai_prefilled" || s === "ai prefilled") {
            return `<span class="doc-card-status-badge doc-card-status-badge--ai">AI Prefilled</span>`;
        }
        const label = s === "new" ? "New" : esc(s.replace(/_/g, " "));
        return `<span class="doc-card-status-badge doc-card-status-badge--new">${label}</span>`;
    }

    const ICON_PACK = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M13 7H3v6a1 1 0 001 1h8a1 1 0 001-1V7z"/><path d="M3 7l1.5-4h7L13 7"/><line x1="8" y1="9.5" x2="8" y2="12.5"/><line x1="6.5" y1="11" x2="9.5" y2="11"/></svg>`;
    const ICON_DL   = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="1.5" x2="8" y2="10"/><polyline points="5,7 8,10 11,7"/><path d="M2 13v.5a.5.5 0 00.5.5h11a.5.5 0 00.5-.5V13"/></svg>`;

    function hasIssue(p) {
        if (p.overall_status) return p.overall_status === "non_compliant";
        return CERT_KEYS.some((k) => {
            const s = (p[k] || "missing").toLowerCase();
            return s === "expired" || s === "missing";
        });
    }

    function hasExpiring(p) {
        if (p.overall_status) return p.overall_status === "at_risk";
        return CERT_KEYS.some((k) => {
            const s = (p[k] || "").toLowerCase();
            return s === "expiring_soon" || s === "expiring";
        });
    }

    function isCompliantPanel(p) {
        if (p.overall_status) return p.overall_status === "compliant";
        return CERT_KEYS.every((k) => {
            const s = (p[k] || "missing").toLowerCase();
            return s === "valid" || s === "expiring_soon" || s === "expiring";
        });
    }

    function passesFilter(p) {
        if (activeFilter === "issues") return hasIssue(p);
        if (activeFilter === "expiring") return hasExpiring(p);
        if (activeFilter === "compliant") return isCompliantPanel(p);
        return true;
    }

    function passesSearch(p) {
        const q = listSearch.trim().toLowerCase();
        if (!q) return true;
        const addr = (p.property_address || "").toLowerCase();
        const pc = extractPostcode(p.property_address || "").toLowerCase();
        return addr.includes(q) || pc.includes(q);
    }

    function filteredProperties() {
        return allProperties.filter((p) => passesFilter(p) && passesSearch(p));
    }

    function renderPropertyList() {
        const root = document.getElementById("props-property-list");
        if (!root) return;

        const rows = filteredProperties();
        if (!rows.length) {
            root.innerHTML =
                '<div class="props-list-empty">No properties match your filters.</div>';
            return;
        }

        root.innerHTML = rows
            .map((p) => {
                const id = p.property_id;
                const pc = extractPostcode(p.property_address);
                const addrLine = esc(addressWithoutPostcode(p.property_address, pc));
                const active = selectedPropertyId === id ? " props-prop-row--active" : "";

                // Read status from nested compliance object; fall back to flat field.
                const badges = CERT_KEYS.map((k) => {
                    const certInfo = (p.compliance && p.compliance[k]) || {};
                    const st = certInfo.status || p[k] || "missing";
                    const cls = certBadgeClass(st);
                    const short = CERT_SHORT[k];
                    const titleText = certInfo.expiry_date
                        ? `${k}: ${st} (expires ${certInfo.expiry_date})`
                        : `${k}: ${st}`;
                    return `<span class="props-cert-badge ${cls}" title="${esc(titleText)}">${esc(short)}</span>`;
                }).join("");

                const dotClass = propertyStatusDotClass(p);
                const isUnassigned = (p.property_address || "").toLowerCase() === "unassigned property";
                const tenantName = p.tenant_name || null;
                const tenantHtml = tenantName
                    ? `<div class="props-prop-tenant">${esc(tenantName)}</div>`
                    : `<div class="props-prop-tenant props-prop-tenant--placeholder">—</div>`;
                const docCount = p.doc_count ?? p.total_documents ?? 0;
                return `
                <button type="button" class="props-prop-row${active}" data-property-id="${id}" role="option">
                    <span class="props-prop-status-dot ${dotClass}" aria-hidden="true"></span>
                    <div class="props-prop-address">${addrLine}</div>
                    ${isUnassigned ? '<div class="props-prop-unassigned-hint">Needs review \u2014 missing property address</div>' : ""}
                    ${pc ? `<div class="props-prop-postcode">${esc(pc)}</div>` : ""}
                    ${tenantHtml}
                    <div class="props-prop-meta">
                        <span class="props-prop-doc-count">${docCount} docs</span>
                        <div class="props-prop-badges">${badges}</div>
                    </div>
                </button>`;
            })
            .join("");

        root.querySelectorAll(".props-prop-row").forEach((btn) => {
            btn.addEventListener("click", () => {
                const id = parseInt(btn.getAttribute("data-property-id"), 10);
                if (Number.isFinite(id)) selectProperty(id);
            });
        });

        // Auto-select the first visible property whenever the displayed list
        // doesn't include the currently selected one (covers initial load,
        // filter changes, and search changes).
        const selectedInResults = selectedPropertyId !== null &&
            rows.some((p) => p.property_id === selectedPropertyId);
        if (!selectedInResults) {
            selectProperty(rows[0].property_id);
        }
    }

    function formatDate(iso) {
        if (!iso) return "—";
        const d = new Date(iso);
        if (Number.isNaN(d.getTime())) return String(iso).slice(0, 10);
        return d.toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
        });
    }

    function complianceLabel(status) {
        const s = (status || "").toLowerCase();
        if (s === "valid") return "Valid";
        if (s === "expiring" || s === "expiring_soon") return "Expiring";
        if (s === "expired") return "Expired";
        return "Missing";
    }

    // Map any status string to the CSS modifier used for compliance chips.
    // "expiring" (new API) and "expiring_soon" (detail API) both map to
    // "expiring-soon" so both use the amber chip class.
    function compChipModifier(status) {
        const s = (status || "missing").toLowerCase();
        if (s === "expiring" || s === "expiring_soon") return "expiring-soon";
        return s.replace(/_/g, "-");
    }

    /** Returns the hex fill colour for a compliance status dot. */
    function dotColorForStatus(status) {
        const s = (status || "missing").toLowerCase();
        if (s === "valid") return "#4ADE80";
        if (s === "expiring" || s === "expiring_soon") return "#F59E0B";
        if (s === "expired") return "#EF4444";
        return "#6B7280";
    }

    function renderComplianceStrip(detail) {
        const el = document.getElementById("props-compliance-strip");
        if (!el) return;

        const byType = detail.documents_by_type || {};
        const totalDocs = Object.values(byType).reduce((n, arr) => n + (arr || []).length, 0);

        const certTypes = [
            { key: "gas_safety" },
            { key: "eicr" },
            { key: "epc" },
            { key: "deposit" },
        ];

        const itemsHtml = certTypes.map(({ key }) => {
            const info = (detail.compliance && detail.compliance[key]) || {};
            const status = (info.status || "missing").toLowerCase();
            const dotColor = dotColorForStatus(status);
            const docTypeName = COMP_TO_DOCTYPE[key];
            const count = (byType[docTypeName] || []).length;
            const label = COMP_STRIP_LABELS[key];
            const isActive = activeComplianceFilter === key;
            const activeClass = isActive ? " props-cert-strip-item--active" : "";

            return `<button type="button" class="props-cert-strip-item${activeClass}" data-comp-filter="${esc(key)}" title="${esc(label)}: ${esc(complianceLabel(status))}">
                <span class="props-cert-dot" style="background:${dotColor};" aria-hidden="true"></span>
                <span>${esc(label)} <span class="props-cert-strip-count">(${count})</span></span>
            </button>`;
        });

        const allActive = activeComplianceFilter === null;
        itemsHtml.push(
            `<button type="button" class="props-cert-strip-item${allActive ? " props-cert-strip-item--active" : ""}" data-comp-filter="__all__">
                All documents <span class="props-cert-strip-count">(${totalDocs})</span>
            </button>`
        );

        el.innerHTML = itemsHtml.join("");

        el.querySelectorAll(".props-cert-strip-item").forEach((btn) => {
            btn.addEventListener("click", () => {
                const key = btn.getAttribute("data-comp-filter");
                if (key === "__all__") {
                    activeComplianceFilter = null;
                } else if (activeComplianceFilter === key) {
                    // Toggle off — same item clicked again
                    activeComplianceFilter = null;
                } else {
                    activeComplianceFilter = key;
                }
                renderComplianceStrip(detail);
                renderDocumentTabsAndCards(detail);
            });
        });
    }

    function docTypeLabelClass(slug) {
        const s = (slug || "").toLowerCase();
        if (s.includes("gas")) return "props-doc-type--gas";
        if (s === "eicr") return "props-doc-type--eicr";
        if (s === "epc") return "props-doc-type--epc";
        if (s.includes("deposit")) return "props-doc-type--deposit";
        if (s.includes("tenancy")) return "props-doc-type--tenancy";
        return "props-doc-type--other";
    }

    function renderKeyFields(fields, isUnknown) {
        const obj = fields || {};
        const keys = Object.keys(obj).slice(0, 6);
        if (!keys.length) {
            const msg = isUnknown ? "Pending review" : "No extracted fields";
            return `<p class="props-doc-fields-empty">${msg}</p>`;
        }
        return `<dl class="props-doc-fields">${keys
            .map((k) => {
                const f = obj[k] || {};
                const lab = f.label || k;
                const val = f.value != null ? String(f.value) : "";
                return `<div class="props-doc-field"><dt title="${esc(lab)}">${esc(lab)}</dt><dd title="${esc(val)}">${esc(val)}</dd></div>`;
            })
            .join("")}</dl>`;
    }

    /** @type {string|null} documents_by_type group key */
    let activeDocTabKey = null;

    function sortDocs(docs) {
        return docs.slice().sort((a, b) => {
            const ad = a.scanned_at || a.imported_at || a.batch_date || "";
            const bd = b.scanned_at || b.imported_at || b.batch_date || "";
            return (bd || "").localeCompare(ad || "");
        });
    }

    function renderDocumentTabsAndCards(detail) {
        const tabsEl = document.getElementById("props-doc-tabs");
        const cardsEl = document.getElementById("props-doc-cards");
        if (!tabsEl || !cardsEl) return;

        const byType = detail.documents_by_type || {};

        // ── Compliance strip filter active: hide tabs, show matching docs only ──
        if (activeComplianceFilter !== null) {
            tabsEl.hidden = true;
            const docTypeName = COMP_TO_DOCTYPE[activeComplianceFilter];
            const filteredDocs = sortDocs(docTypeName ? byType[docTypeName] || [] : []);
            if (!filteredDocs.length) {
                cardsEl.innerHTML = '<p style="padding:16px 0;font-size:13px;color:#64748b;margin:0;">No documents of this type for this property.</p>';
            } else {
                cardsEl.innerHTML = filteredDocs.map((doc) => cardHtml(doc)).join("");
            }
            return;
        }

        // ── Normal tab-based rendering ──
        tabsEl.hidden = false;

        const typeOrder = [
            "Gas Safety Certificate",
            "EICR",
            "EPC",
            "Deposit Protection Certificate",
            "Tenancy Agreement",
            "Other",
        ];
        const types = Object.keys(byType).sort((a, b) => {
            const ai = typeOrder.indexOf(a);
            const bi = typeOrder.indexOf(b);
            if (ai !== -1 && bi !== -1) return ai - bi;
            if (ai !== -1) return -1;
            if (bi !== -1) return 1;
            return (a || "").localeCompare(b || "");
        });

        if (!types.length) {
            tabsEl.innerHTML = "";
            cardsEl.innerHTML = '<div class="props-detail-empty">No documents for this property.</div>';
            activeDocTabKey = null;
            return;
        }

        if (activeDocTabKey == null || !types.includes(activeDocTabKey)) {
            activeDocTabKey = types[0];
        }

        tabsEl.innerHTML = types
            .map((t) => {
                const active = t === activeDocTabKey ? " props-doc-tab--active" : "";
                const n = (byType[t] || []).length;
                const enc = encodeURIComponent(t);
                return `<button type="button" class="props-doc-tab${active}" data-doc-tab="${enc}">${esc(t)} <span class="props-doc-tab-n">${n}</span></button>`;
            })
            .join("");

        tabsEl.querySelectorAll(".props-doc-tab").forEach((btn) => {
            btn.addEventListener("click", () => {
                const raw = btn.getAttribute("data-doc-tab") || "";
                try {
                    activeDocTabKey = decodeURIComponent(raw);
                } catch {
                    activeDocTabKey = raw;
                }
                renderDocumentTabsAndCards(detail);
            });
        });

        const docs = sortDocs(byType[activeDocTabKey] || []);
        cardsEl.innerHTML = docs.map((doc) => cardHtml(doc)).join("");
    }

    function cardHtml(doc) {
        const id = doc.id;
        const slug = doc.doc_type_slug || "";
        const unknown = isUnknownType(doc);
        const typeClass = unknown ? "props-doc-type--unknown" : docTypeLabelClass(slug);
        const typeDisplay = unknown ? "Unclassified" : esc(doc.doc_type || "Document");
        const title = doc.doc_name || (unknown ? "Unclassified Document" : doc.doc_type || "Document");
        const pdfHref = withClientQuery("/api/documents/by-id/" + id + "/pdf");

        return `
        <article class="props-doc-card">
            <div class="props-doc-card-top">
                <span class="props-doc-type-label ${typeClass}">${typeDisplay}</span>
                <div class="props-doc-card-controls">
                    ${docStatusBadgeHtml(doc)}
                    <button type="button" class="props-btn-icon atp-trigger" data-document-id="${id}" title="Add to Pack">${ICON_PACK}</button>
                    <a class="props-btn-icon" href="${pdfHref}" target="_blank" rel="noopener" title="Download PDF">${ICON_DL}</a>
                </div>
            </div>
            <h3 class="props-doc-title">${esc(title)}</h3>
            ${renderKeyFields(doc.fields || doc.document_fields, unknown)}
        </article>`;
    }

    function renderRightPanel(detail) {
        const empty = document.getElementById("props-detail-empty");
        const content = document.getElementById("props-detail-content");
        if (empty) empty.hidden = true;
        if (content) content.hidden = false;

        const titleEl = document.getElementById("props-detail-title");
        const metaEl = document.getElementById("props-detail-meta");
        if (titleEl) titleEl.textContent = detail.property_address || "Property";
        if (metaEl) {
            const parts = [detail.client_name || ""];
            const t = detail.tenant;
            if (t && (t.name || t.tenant_name)) parts.push((t.name || t.tenant_name).trim());
            metaEl.textContent = parts.filter(Boolean).join(" · ") || "—";
        }

        activeDocTabKey = null;
        activeComplianceFilter = null;
        renderComplianceStrip(detail);
        renderDocumentTabsAndCards(detail);

        const existingBanner = document.getElementById("props-unassigned-banner");
        if (existingBanner) existingBanner.remove();
        const isUnassigned = (detail.property_address || "").toLowerCase() === "unassigned property";
        if (isUnassigned) {
            const docsSection = document.querySelector(".props-docs-section");
            if (docsSection) {
                const banner = document.createElement("div");
                banner.id = "props-unassigned-banner";
                banner.className = "props-unassigned-banner";
                banner.textContent = "These documents are missing a property address. Open ReviewStation to add the address, then run a sync to reassign them.";
                docsSection.insertBefore(banner, docsSection.firstChild);
            }
        }
    }

    function showRightEmpty(message) {
        const empty = document.getElementById("props-detail-empty");
        const content = document.getElementById("props-detail-content");
        const loading = document.getElementById("props-detail-loading");
        if (loading) loading.hidden = true;
        if (content) content.hidden = true;
        if (empty) {
            empty.hidden = false;
            const t = empty.querySelector(".props-detail-empty-text");
            if (t) t.textContent = message || "Select a property";
        }
    }

    function showLoading(show) {
        const loading = document.getElementById("props-detail-loading");
        const content = document.getElementById("props-detail-content");
        if (!loading) return;
        loading.hidden = !show;
        if (show && content) content.hidden = true;
    }

    async function selectProperty(propertyId) {
        selectedPropertyId = propertyId;
        renderPropertyList();

        showLoading(true);
        const empty = document.getElementById("props-detail-empty");
        if (empty) empty.hidden = true;

        try {
            const res = await fetch(withClientQuery(`/api/properties/${propertyId}`), {
                credentials: "same-origin",
            });
            if (!res.ok) throw new Error("Failed to load property");
            const data = await res.json();
            const detail = data.property || data;
            showLoading(false);
            renderRightPanel(detail);
        } catch (e) {
            console.error(e);
            showLoading(false);
            showRightEmpty("Could not load property details.");
        }
    }

    async function loadProperties() {
        const root = document.getElementById("props-property-list");
        if (root) {
            root.innerHTML = '<div class="props-list-loading">Loading properties…</div>';
        }
        try {
            const res = await fetch(withClientQuery("/api/properties"), { credentials: "same-origin" });
            const data = await res.json().catch(() => ({}));
            allProperties = data.properties || [];
            if (!allProperties.length) {
                // Genuine empty portfolio — nothing to select
                if (root) root.innerHTML = '<div class="props-list-empty">No properties in this portfolio.</div>';
                showRightEmpty("No properties in this portfolio.");
                return;
            }
            // renderPropertyList auto-selects the first visible property when
            // nothing is currently selected, so no manual selectProperty needed.
            renderPropertyList();
        } catch (e) {
            console.error(e);
            if (root) {
                root.innerHTML = '<div class="props-list-empty">Failed to load properties.</div>';
            }
        }
    }

    function bindFilters() {
        document.querySelectorAll(".props-filter-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                const f = btn.getAttribute("data-filter") || "all";
                activeFilter = f;
                document.querySelectorAll(".props-filter-btn").forEach((b) => {
                    b.classList.toggle("props-filter-btn--active", b.getAttribute("data-filter") === f);
                });
                renderPropertyList();
            });
        });

        const search = document.getElementById("props-list-search");
        if (search) {
            search.addEventListener("input", () => {
                listSearch = search.value || "";
                renderPropertyList();
            });
        }
    }

    function init() {
        if (!document.querySelector('[data-page="properties"]')) return;
        bindFilters();
        loadProperties();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
