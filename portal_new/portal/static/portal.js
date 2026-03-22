/**
 * MorphIQ Portal — Document Archive Viewer
 * Search-first retrieval interface with detail drawer.
 */

(function () {
    "use strict";

    // ── State ───────────────────────────────────────────────────────────────
    let allDocuments = [];
    let filteredDocuments = [];
    let selectedDocId = null;
    let activeFilter = "all";
    let currentSort = "newest";
    let searchQuery = "";
    let searchDebounce = null;

    // ── DOM refs (populated on init) ────────────────────────────────────────
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    // ── Doc type icons ──────────────────────────────────────────────────────
    const DOC_ICONS = {
        "Tenancy Agreement": "📄",
        "Gas Safety Certificate": "🔥",
        "EICR": "⚡",
        "EPC": "🏠",
        "Deposit Protection": "🛡️",
        "Inventory": "📋",
    };

    // ── Formatting helpers ──────────────────────────────────────────────────
    function statusClass(status) {
        if (!status) return "status-new";
        const s = status.toLowerCase().replace(/\s+/g, "-");
        const map = {
            "verified": "status-verified",
            "active": "status-active",
            "needs-review": "status-needs-review",
            "needs_review": "status-needs-review",
            "new": "status-new",
            "failed": "status-failed",
            "expiring-soon": "status-expiring",
            "expiring": "status-expiring",
            "ai-prefilled": "status-ai-prefilled",
            "ai_prefilled": "status-ai_prefilled",
        };
        return map[s] || "status-new";
    }

    function statusLabel(status) {
        if (!status) return "New";
        const labels = {
            "ai_prefilled": "AI Prefilled",
            "ai-prefilled": "AI Prefilled",
            "needs_review": "Needs Review",
            "verified": "Verified",
        };
        const lower = status.toLowerCase();
        if (labels[lower]) return labels[lower];
        return status.replace(/[_-]/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    }

    function cleanDocName(doc) {
        // Generate a clean display name from doc type + property address
        const docType = doc.doc_type || "Document";
        const address = doc.property_address;
        if (address && address !== "Unassigned property") {
            // Shorten address: take first line / unit
            const shortAddr = address.split(",")[0].trim();
            return docType + " — " + shortAddr;
        }
        return docType;
    }

    function formatDate(dateStr) {
        if (!dateStr) return "—";
        // Handle ISO and common formats
        const d = new Date(dateStr);
        if (isNaN(d)) return dateStr;
        return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
    }

    function docIcon(docType) {
        return DOC_ICONS[docType] || "📄";
    }

    function fieldLabel(key) {
        return key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    }

    // ── API ─────────────────────────────────────────────────────────────────
    async function fetchDocuments() {
        try {
            const res = await fetch("/api/documents?limit=500");
            const data = await res.json();
            allDocuments = data.documents || [];
            applyFilters();
            updateStats();
        } catch (err) {
            console.error("Failed to fetch documents:", err);
            showEmptyState("Failed to load documents. Is the server running?");
        }
    }

    async function fetchDocumentDetail(sourceDocId) {
        try {
            const res = await fetch(`/api/documents/${encodeURIComponent(sourceDocId)}`);
            if (!res.ok) return null;
            return await res.json();
        } catch (err) {
            console.error("Failed to fetch document detail:", err);
            return null;
        }
    }

    // ── Filter & Search ─────────────────────────────────────────────────────
    function applyFilters() {
        let docs = [...allDocuments];

        // Type filter
        if (activeFilter !== "all") {
            const slug = activeFilter;
            docs = docs.filter(d => (d.doc_type_slug || "") === slug || (d.doc_type || "").toLowerCase().replace(/\s+/g, "-") === slug);
        }

        // Search
        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            docs = docs.filter(d =>
                (d.source_doc_id || "").toLowerCase().includes(q) ||
                (d.doc_name || "").toLowerCase().includes(q) ||
                (d.doc_type || "").toLowerCase().includes(q) ||
                (d.property_address || "").toLowerCase().includes(q) ||
                (d.client_name || "").toLowerCase().includes(q) ||
                (d.status || "").toLowerCase().includes(q) ||
                (d.reviewed_by || "").toLowerCase().includes(q)
            );
        }

        // Sort
        docs.sort((a, b) => {
            switch (currentSort) {
                case "newest":
                    return (b.scanned_at || b.imported_at || "").localeCompare(a.scanned_at || a.imported_at || "");
                case "oldest":
                    return (a.scanned_at || a.imported_at || "").localeCompare(b.scanned_at || b.imported_at || "");
                case "name":
                    return (a.doc_name || "").localeCompare(b.doc_name || "");
                case "status":
                    return (a.status || "").localeCompare(b.status || "");
                default:
                    return 0;
            }
        });

        filteredDocuments = docs;
        renderTable();
        updateSearchCount();
    }

    // ── Stats ───────────────────────────────────────────────────────────────
    function updateStats() {
        const total = allDocuments.length;
        const verified = allDocuments.filter(d => (d.status || "").toLowerCase() === "verified").length;
        const active = allDocuments.filter(d => (d.status || "").toLowerCase() === "active").length;
        const needsReview = allDocuments.filter(d => {
            const s = (d.status || "").toLowerCase();
            return s === "needs review" || s === "needs_review" || s === "new" || s === "ai_prefilled" || s === "ai-prefilled";
        }).length;

        const statTotal = $("#stat-total");
        const statVerified = $("#stat-verified");
        const statReview = $("#stat-review");

        if (statTotal) statTotal.textContent = total;
        if (statVerified) statVerified.textContent = verified + active;
        if (statReview) statReview.textContent = needsReview;
    }

    function updateSearchCount() {
        const el = $("#search-count");
        if (!el) return;
        if (searchQuery) {
            el.textContent = `${filteredDocuments.length} result${filteredDocuments.length !== 1 ? "s" : ""}`;
            el.style.display = "block";
        } else {
            el.style.display = "none";
        }
    }

    // ── Render Table ────────────────────────────────────────────────────────
    function renderTable() {
        const tbody = $("#results-body");
        if (!tbody) return;

        if (filteredDocuments.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-state">
                        ${searchQuery ? "No documents match your search." : "No documents found."}
                    </td>
                </tr>`;
            return;
        }

        tbody.innerHTML = filteredDocuments.map(doc => {
            const icon = docIcon(doc.doc_type);
            const isSelected = doc.source_doc_id === selectedDocId;
            const scannedDate = formatDate(doc.scanned_at || doc.imported_at);

            return `
                <tr class="${isSelected ? "selected" : ""}" data-doc-id="${doc.source_doc_id}">
                    <td>
                        <span class="cell-doctype">
                            <span class="cell-doctype-icon">${icon}</span>
                            ${doc.doc_type || "Unknown"}
                        </span>
                    </td>
                    <td>
                        <div class="cell-property">${doc.property_address || "—"}</div>
                    </td>
                    <td>
                        <span class="cell-date">${scannedDate}</span>
                    </td>
                    <td>
                        <span class="status-badge ${statusClass(doc.status)}">
                            <span class="dot"></span>
                            ${statusLabel(doc.status)}
                        </span>
                    </td>
                    <td>
                        <span class="cell-docid">${doc.source_doc_id || "—"}</span>
                    </td>
                </tr>`;
        }).join("");

        // Bind row clicks
        tbody.querySelectorAll("tr[data-doc-id]").forEach(row => {
            row.addEventListener("click", () => {
                const docId = row.getAttribute("data-doc-id");
                selectDocument(docId);
            });
        });
    }

    // ── Select Document → Open Drawer ───────────────────────────────────────
    async function selectDocument(sourceDocId) {
        selectedDocId = sourceDocId;

        // Highlight selected row
        $$(".results-table tbody tr").forEach(row => {
            row.classList.toggle("selected", row.getAttribute("data-doc-id") === sourceDocId);
        });

        // Show drawer
        const drawer = $("#detail-drawer");
        if (!drawer) return;
        drawer.classList.remove("hidden");

        // Find doc in local data first
        const localDoc = allDocuments.find(d => d.source_doc_id === sourceDocId);
        if (localDoc) {
            renderDrawer(localDoc);
        }

        // Also fetch full detail (with fields) from API
        const fullDoc = await fetchDocumentDetail(sourceDocId);
        if (fullDoc && fullDoc.source_doc_id === selectedDocId) {
            renderDrawer(fullDoc);
        }
    }

    function closeDrawer() {
        selectedDocId = null;
        const drawer = $("#detail-drawer");
        if (drawer) drawer.classList.add("hidden");
        $$(".results-table tbody tr").forEach(row => row.classList.remove("selected"));
    }

    // ── Render Drawer ───────────────────────────────────────────────────────
    function renderDrawer(doc) {
        // Header
        const metaIcon = $(".drawer-meta-icon");
        const docIdEl = $(".drawer-docid");
        const titleEl = $(".drawer-title");
        const addressEl = $(".drawer-address");
        const statusEl = $(".drawer-status");

        if (metaIcon) metaIcon.textContent = docIcon(doc.doc_type);
        if (docIdEl) docIdEl.textContent = doc.source_doc_id || "";
        if (titleEl) titleEl.textContent = cleanDocName(doc);
        if (addressEl) addressEl.textContent = doc.property_address || "No address";
        if (statusEl) {
            statusEl.innerHTML = `
                <span class="status-badge ${statusClass(doc.status)}">
                    <span class="dot"></span>
                    ${statusLabel(doc.status)}
                </span>`;
        }

        // Summary tab - fields
        const fieldGroup = $(".field-group");
        if (fieldGroup) {
            const fields = doc.fields || {};
            const fieldKeys = Object.keys(fields);

            // Also add core document info
            let html = "";

            // Always show these core fields
            const coreFields = [
                ["Document Name", doc.doc_name],
                ["Client", doc.client_name],
                ["Property", doc.property_address],
                ["Scanned", formatDate(doc.scanned_at || doc.imported_at)],
                ["Batch Date", doc.batch_date || "—"],
            ];

            coreFields.forEach(([label, value]) => {
                if (value && value !== "—") {
                    html += `
                        <div class="field-item">
                            <div class="field-item-label">${label}</div>
                            <div class="field-item-value">${value}</div>
                        </div>`;
                }
            });

            // Extracted fields from document_fields
            if (fieldKeys.length > 0) {
                html += `
                    <div class="field-item" style="margin-top: 10px; padding-top: 14px; border-top: 1px solid var(--border);">
                        <div class="field-item-label" style="color: var(--accent); font-size: 10px;">Verified Fields</div>
                    </div>`;
                fieldKeys.forEach(key => {
                    const f = fields[key];
                    html += `
                        <div class="field-item">
                            <div class="field-item-label">${f.label || fieldLabel(key)}</div>
                            <div class="field-item-value">${f.value || "—"}</div>
                        </div>`;
                });
            } else {
                html += `
                    <div class="no-fields">
                        <div class="no-fields-icon">📋</div>
                        No verified fields extracted yet.
                    </div>`;
            }

            fieldGroup.innerHTML = html;
        }

        // Review section
        const reviewSection = $(".review-section");
        if (reviewSection) {
            if (doc.reviewed_by) {
                reviewSection.style.display = "block";
                reviewSection.innerHTML = `
                    <div class="field-item-label">Verification</div>
                    <div class="review-info">
                        Verified by <strong>${doc.reviewed_by}</strong><br>
                        ${formatDate(doc.reviewed_at)}
                    </div>`;
            } else {
                reviewSection.style.display = "none";
            }
        }

        // PDF preview
        const pdfContainer = $(".pdf-preview-container");
        if (pdfContainer) {
            if (doc.pdf_path) {
                // Encode the path for URL
                const pdfUrl = `/pdf/${encodeURIComponent(doc.pdf_path)}`;
                pdfContainer.innerHTML = `<iframe src="${pdfUrl}" title="PDF Preview"></iframe>`;
            } else {
                pdfContainer.innerHTML = `
                    <div class="pdf-placeholder">
                        <svg class="pdf-placeholder-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                            <polyline points="14 2 14 8 20 8"/>
                            <line x1="16" y1="13" x2="8" y2="13"/>
                            <line x1="16" y1="17" x2="8" y2="17"/>
                        </svg>
                        <span class="pdf-placeholder-text">PDF not available</span>
                        <span class="pdf-placeholder-name">${doc.source_doc_id || ""}</span>
                    </div>`;
            }
        }

        // Open PDF button
        const openPdfBtn = $(".btn-open-pdf");
        if (openPdfBtn) {
            if (doc.pdf_path) {
                openPdfBtn.onclick = () => {
                    window.open(`/pdf/${encodeURIComponent(doc.pdf_path)}`, "_blank");
                };
                openPdfBtn.disabled = false;
                openPdfBtn.style.opacity = "1";
            } else {
                openPdfBtn.disabled = true;
                openPdfBtn.style.opacity = "0.4";
            }
        }

        // Download button
        const downloadBtn = $(".btn-download");
        if (downloadBtn) {
            if (doc.pdf_path) {
                downloadBtn.onclick = () => {
                    const a = document.createElement("a");
                    a.href = `/pdf/${encodeURIComponent(doc.pdf_path)}`;
                    a.download = `${doc.source_doc_id || "document"}.pdf`;
                    a.click();
                };
                downloadBtn.disabled = false;
                downloadBtn.style.opacity = "1";
            } else {
                downloadBtn.disabled = true;
                downloadBtn.style.opacity = "0.4";
            }
        }
    }

    function showEmptyState(message) {
        const tbody = $("#results-body");
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-state">${message}</td></tr>`;
        }
    }

    // ── Drawer Tab Switching ────────────────────────────────────────────────
    function switchDrawerTab(tabName) {
        $$(".drawer-tab").forEach(tab => {
            tab.classList.toggle("active", tab.getAttribute("data-tab") === tabName);
        });
        $$(".tab-panel").forEach(panel => {
            panel.classList.toggle("active", panel.getAttribute("data-tab") === tabName);
        });
    }

    // ── Init ────────────────────────────────────────────────────────────────
    function init() {
        // #region agent log
        fetch('http://127.0.0.1:7655/ingest/814a10d9-1e67-436f-8e4c-0c9d8d30f299', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Debug-Session-Id': 'c11422',
            },
            body: JSON.stringify({
                sessionId: 'c11422',
                runId: 'pre-fix',
                hypothesisId: 'H2',
                location: 'portal_new/portal/static/portal.js:init',
                message: 'Legacy portal init reached',
                data: {
                    path: window.location.pathname,
                },
                timestamp: Date.now(),
            }),
        }).catch(() => {});
        // #endregion agent log
        // Search input
        const searchInput = $(".search-input");
        if (searchInput) {
            searchInput.addEventListener("input", (e) => {
                searchQuery = e.target.value;
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => applyFilters(), 150);
            });
        }

        // Filter chips
        $$(".filter-chip").forEach(chip => {
            chip.addEventListener("click", () => {
                activeFilter = chip.getAttribute("data-filter");
                $$(".filter-chip").forEach(c => c.classList.toggle("active", c === chip));
                applyFilters();
            });
        });

        // Sort select
        const sortSelect = $(".sort-select");
        if (sortSelect) {
            sortSelect.addEventListener("change", (e) => {
                currentSort = e.target.value;
                applyFilters();
            });
        }

        // Drawer close button
        const closeBtn = $(".drawer-close");
        if (closeBtn) {
            closeBtn.addEventListener("click", closeDrawer);
        }

        // Drawer tabs
        $$(".drawer-tab").forEach(tab => {
            tab.addEventListener("click", () => {
                switchDrawerTab(tab.getAttribute("data-tab"));
            });
        });

        // Keyboard: Escape to close drawer
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && selectedDocId) {
                closeDrawer();
            }
        });

        // Load documents
        fetchDocuments();
    }

    // Run on DOM ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
