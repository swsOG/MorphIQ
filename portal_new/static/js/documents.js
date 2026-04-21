/**
 * MorphIQ /documents — searchable document library.
 */
(function () {
    const DEBOUNCE_MS = 300;
    const FETCH_LIMIT = 500;

    const TYPE_SLUGS = {
        all: "",
        gas: "gas-safety-certificate",
        eicr: "eicr",
        epc: "epc",
        tenancy: "tenancy-agreement",
        deposit: "deposit-protection",
        inventory: "inventory",
    };

    let rawDocuments = [];
    let searchTimer = null;
    let activeTypeKey = "all";
    let activeStatusKey = "all";
    let activeSort = "newest";
    let viewMode = "list";

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

    function flatFields(doc) {
        const f = doc.fields || doc.document_fields || {};
        const out = {};
        Object.keys(f).forEach(function (k) {
            const meta = f[k];
            out[k] = typeof meta === "object" && meta && "value" in meta ? String(meta.value || "").trim() : String(meta || "").trim();
        });
        return out;
    }

    /** Mirrors COMPLIANCE_EXPIRY_FIELDS in app.py */
    function expiryFieldListForSlug(slug) {
        const s = String(slug || "").toLowerCase();
        if (!s) return null;
        if (s.includes("gas")) return ["expiry_date", "next_inspection_date"];
        if (s === "eicr") return ["next_inspection_date", "expiry_date"];
        if (s === "epc") return ["valid_until", "expiry_date"];
        if (s.includes("deposit")) return ["expiry_date", "valid_until"];
        return null;
    }

    function parseDate(value) {
        if (!value || !String(value).trim()) return null;
        const v = String(value).trim();
        const iso = v.match(/^(\d{4}-\d{2}-\d{2})/);
        if (iso) {
            const d = new Date(iso[1] + "T12:00:00");
            return Number.isNaN(d.getTime()) ? null : d;
        }
        const d = new Date(v);
        return Number.isNaN(d.getTime()) ? null : d;
    }

    /**
     * @returns {"valid"|"expiring_soon"|"expired"|"no_expiry"|null}
     */
    function complianceBucket(doc) {
        const slug = doc.doc_type_slug || "";
        const flat = flatFields(doc);
        const keys = expiryFieldListForSlug(slug);
        if (!keys) return null;

        let expiryStr = "";
        for (let i = 0; i < keys.length; i++) {
            const raw = flat[keys[i]];
            if (raw && String(raw).trim()) {
                expiryStr = String(raw).trim();
                break;
            }
        }
        if (!expiryStr) return "no_expiry";

        const expiryDate = parseDate(expiryStr);
        if (!expiryDate) return "no_expiry";

        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const exp = new Date(expiryDate);
        exp.setHours(0, 0, 0, 0);
        const daysUntil = Math.round((exp - today) / 86400000);

        if (daysUntil < 0) return "expired";
        if (daysUntil <= 30) return "expiring_soon";
        return "valid";
    }

    function isNeedsReviewWorkflow(doc) {
        const s = String(doc.status || "").toLowerCase();
        return s === "needs_review" || s === "new" || s === "ai_prefilled";
    }

    function docTypeLabelClass(slug) {
        const s = (slug || "").toLowerCase();
        if (s.includes("gas")) return "props-doc-type--gas";
        if (s === "eicr") return "props-doc-type--eicr";
        if (s === "epc") return "props-doc-type--epc";
        if (s.includes("deposit")) return "props-doc-type--deposit";
        if (s.includes("tenancy")) return "props-doc-type--tenancy";
        if (s.includes("inventory")) return "props-doc-type--inventory";
        return "props-doc-type--other";
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
        const label = s === "new" ? "New" : String(s).replace(/_/g, " ");
        return `<span class="doc-card-status-badge doc-card-status-badge--new">${label}</span>`;
    }

    const ICON_PACK = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M13 7H3v6a1 1 0 001 1h8a1 1 0 001-1V7z"/><path d="M3 7l1.5-4h7L13 7"/><line x1="8" y1="9.5" x2="8" y2="12.5"/><line x1="6.5" y1="11" x2="9.5" y2="11"/></svg>`;
    const ICON_DL   = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="1.5" x2="8" y2="10"/><polyline points="5,7 8,10 11,7"/><path d="M2 13v.5a.5.5 0 00.5.5h11a.5.5 0 00.5-.5V13"/></svg>`;

    function formatDate(iso) {
        if (!iso) return "—";
        const d = new Date(iso);
        if (Number.isNaN(d.getTime())) return String(iso).slice(0, 10);
        return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    }

    function scanDate(doc) {
        return doc.scanned_at || doc.batch_date || doc.reviewed_at || doc.imported_at || "";
    }

    function renderKeyFields(doc, isUnknown) {
        const obj = doc.fields || {};
        const keys = Object.keys(obj).slice(0, 4);
        if (!keys.length) {
            const msg = isUnknown ? "Pending review" : "No extracted fields";
            return `<p class="props-doc-fields-empty doc-lib-no-fields">${msg}</p>`;
        }
        return `<dl class="props-doc-fields doc-lib-fields">${keys
            .map(function (k) {
                const f = obj[k] || {};
                const lab = f.label || k;
                const val = f.value != null ? String(f.value) : "";
                return `<div class="props-doc-field"><dt title="${esc(lab)}">${esc(lab)}</dt><dd title="${esc(val)}">${esc(val)}</dd></div>`;
            })
            .join("")}</dl>`;
    }

    function cardHtml(doc) {
        const id = doc.id;
        const slug = doc.doc_type_slug || "";
        const unknown = isUnknownType(doc);
        const typeClass = unknown ? "props-doc-type--unknown" : docTypeLabelClass(slug);
        const typeDisplay = unknown ? "Unclassified" : esc(doc.doc_type || "Document");
        const title = doc.doc_name || (unknown ? "Unclassified Document" : doc.doc_type || "Document");
        const pdfHref = withClientQuery("/api/documents/by-id/" + id + "/pdf");
        const detailHref = withClientQuery("/document/by-id/" + id);
        const reviewLabel = isNeedsReviewWorkflow(doc) ? "Review" : "View";
        const addr = doc.property_address || "—";
        const scanned = formatDate(scanDate(doc));

        return `
        <article class="props-doc-card doc-lib-card" data-doc-id="${id}">
            <div class="props-doc-card-top">
                <span class="props-doc-type-label ${typeClass}">${typeDisplay}</span>
                <div class="props-doc-card-controls">
                    ${docStatusBadgeHtml(doc)}
                    <button type="button" class="props-btn-icon portal-action-btn portal-action-btn--icon atp-trigger" data-document-id="${id}" title="Add to Pack">${ICON_PACK}</button>
                    <a class="props-btn-icon portal-action-btn portal-action-btn--icon" href="${pdfHref}" target="_blank" rel="noopener" title="Download PDF">${ICON_DL}</a>
                </div>
            </div>
            <h3 class="props-doc-title">${esc(title)}</h3>
            <p class="doc-lib-property-line">${esc(addr)}</p>
            ${renderKeyFields(doc, unknown)}
            <p class="doc-lib-scan-meta">Scan date · ${esc(scanned)}</p>
            <div class="doc-lib-card-actions">
                <a class="props-btn props-btn-review portal-action-btn portal-action-btn--primary" href="${detailHref}">${reviewLabel}</a>
            </div>
        </article>`;
    }

    function rowHtml(doc) {
        const id = doc.id;
        const slug = doc.doc_type_slug || "";
        const typeClass = docTypeLabelClass(slug);
        const title = doc.doc_name || doc.doc_type || "Document";
        const pdfHref = withClientQuery("/api/documents/by-id/" + id + "/pdf");
        const detailHref = withClientQuery("/document/by-id/" + id);
        const reviewLabel = isNeedsReviewWorkflow(doc) ? "Review" : "View";
        const verified = String(doc.status || "").toLowerCase() === "verified";
        const addr = doc.property_address || "—";
        const scanned = formatDate(scanDate(doc));
        return `
        <tr class="doc-lib-list-row" data-doc-id="${id}">
            <td class="doc-lib-list-cell doc-lib-list-type"><span class="props-doc-type-label ${typeClass}">${esc(doc.doc_type || "—")}</span></td>
            <td class="doc-lib-list-cell doc-lib-list-title">${esc(title)}</td>
            <td class="doc-lib-list-cell doc-lib-list-addr">${esc(addr)}</td>
            <td class="doc-lib-list-cell doc-lib-list-meta">${verified ? "Verified" : esc((doc.status || "—").replace(/_/g, " "))}</td>
            <td class="doc-lib-list-cell doc-lib-list-date">${esc(scanned)}</td>
            <td class="doc-lib-list-cell doc-lib-list-actions">
                <a class="props-btn props-btn-review portal-action-btn portal-action-btn--primary" href="${detailHref}">${reviewLabel}</a>
                <button type="button" class="props-btn props-btn-pack portal-action-btn portal-action-btn--quiet atp-trigger" data-document-id="${id}">Add to Pack</button>
                <a class="props-btn props-btn-pdf portal-action-btn portal-action-btn--quiet" href="${pdfHref}" target="_blank" rel="noopener">Download</a>
            </td>
        </tr>`;
    }

    function render() {
        const grid = document.getElementById("documents-library-grid");
        const listWrap = document.getElementById("documents-library-list-wrap");
        const countEl = document.getElementById("documents-library-count");
        const empty = document.getElementById("documents-library-empty");

        // Backend handles all filtering; render whatever the API returned.
        const docs = rawDocuments;
        if (countEl) countEl.textContent = String(docs.length);

        if (!grid || !listWrap) return;

        if (!docs.length) {
            grid.innerHTML = "";
            listWrap.innerHTML = "";
            grid.hidden = true;
            listWrap.hidden = true;
            if (empty) {
                empty.hidden = false;
                empty.textContent = "No documents match your filters.";
            }
            return;
        }
        if (empty) empty.hidden = true;

        grid.innerHTML = docs.map(cardHtml).join("");
        listWrap.innerHTML =
            `<table class="doc-lib-table" role="grid"><thead><tr>
                <th>Type</th><th>Title</th><th>Property</th><th>Status</th><th>Scan date</th><th>Actions</th>
            </tr></thead><tbody>` +
            docs.map(rowHtml).join("") +
            `</tbody></table>`;

        if (viewMode === "grid") {
            grid.hidden = false;
            listWrap.hidden = true;
        } else {
            grid.hidden = true;
            listWrap.hidden = false;
        }

        document.querySelectorAll(".doc-lib-view-toggle").forEach(function (b) {
            const on = (b.getAttribute("data-view") || "") === viewMode;
            b.classList.toggle("doc-lib-view-toggle--active", on);
            b.setAttribute("aria-pressed", on ? "true" : "false");
        });
    }

    function buildApiUrl() {
        const params = new URLSearchParams();

        const q = ((document.getElementById("documents-library-search") || {}).value || "").trim();
        if (q) params.set("q", q);

        const slug = TYPE_SLUGS[activeTypeKey];
        if (slug) params.set("type", slug);

        // Send the active status to the backend so all filtering is server-side.
        if (activeStatusKey && activeStatusKey !== "all") {
            params.set("status", activeStatusKey);
        }

        params.set("sort", activeSort || "newest");
        params.set("limit", String(FETCH_LIMIT));

        return withClientQuery("/api/documents?" + params.toString());
    }

    async function fetchDocuments() {
        const loading = document.getElementById("documents-library-loading");
        const empty = document.getElementById("documents-library-empty");
        if (loading) loading.hidden = false;

        try {
            const res = await fetch(buildApiUrl(), { credentials: "same-origin" });
            const data = await res.json().catch(function () {
                return {};
            });
            rawDocuments = data.documents || [];
            if (loading) loading.hidden = true;
            if (empty) empty.hidden = true;
            render();
        } catch (e) {
            console.error(e);
            if (loading) loading.hidden = true;
            rawDocuments = [];
            if (empty) {
                empty.textContent = "Failed to load documents.";
                empty.hidden = false;
            }
            render();
        }
    }

    function scheduleFetch() {
        if (searchTimer) clearTimeout(searchTimer);
        searchTimer = setTimeout(function () {
            fetchDocuments();
        }, DEBOUNCE_MS);
    }

    function bind() {
        const search = document.getElementById("documents-library-search");
        if (search) {
            search.addEventListener("input", function () {
                scheduleFetch();
            });
        }

        document.querySelectorAll(".doc-lib-type-pill").forEach(function (btn) {
            btn.addEventListener("click", function () {
                const k = btn.getAttribute("data-doc-type") || "all";
                activeTypeKey = k;
                document.querySelectorAll(".doc-lib-type-pill").forEach(function (b) {
                    b.classList.toggle("doc-lib-pill--active", (b.getAttribute("data-doc-type") || "") === k);
                });
                fetchDocuments();
            });
        });

        document.querySelectorAll(".doc-lib-status-pill").forEach(function (btn) {
            btn.addEventListener("click", function () {
                const k = btn.getAttribute("data-doc-status") || "all";
                activeStatusKey = k;
                document.querySelectorAll(".doc-lib-status-pill").forEach(function (b) {
                    b.classList.toggle("doc-lib-pill--active", (b.getAttribute("data-doc-status") || "") === k);
                });
                fetchDocuments();
            });
        });

        const sortEl = document.getElementById("documents-library-sort");
        if (sortEl) {
            activeSort = sortEl.value || "newest";
            sortEl.addEventListener("change", function () {
                activeSort = sortEl.value || "newest";
                fetchDocuments();
            });
        }

        document.querySelectorAll(".doc-lib-view-toggle").forEach(function (btn) {
            btn.addEventListener("click", function () {
                const mode = btn.getAttribute("data-view") || "grid";
                viewMode = mode;
                document.querySelectorAll(".doc-lib-view-toggle").forEach(function (b) {
                    b.classList.toggle("doc-lib-view-toggle--active", (b.getAttribute("data-view") || "") === mode);
                });
                render();
            });
        });
    }

    function init() {
        if (!document.querySelector('[data-page="documents"]')) return;
        bind();
        fetchDocuments();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
