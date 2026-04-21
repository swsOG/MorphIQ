/**
 * MorphIQ Portal — Document Archive Viewer
 * Search-first retrieval interface with detail drawer.
 */

(function () {
    "use strict";

    // ── State (archive view) ────────────────────────────────────────────────
    let allProperties = [];
    let filteredProperties = [];
    let selectedPropertyId = null;
    let activeFilter = "all";
    let currentSort = "newest";
    let archiveStatusFilter = "all";
    let searchQuery = "";
    let listSearchQuery = "";
    // Left-panel (Archive tab) additional filters
    let archiveAreaFilter = ""; // normalized area key (lowercase)
    let archivePostcodePrefixFilter = ""; // outward postcode prefix, e.g. "CM18"
    let searchDebounce = null;

    /** Archive “Luminous” layout: expandable property tree + document table */
    const ARCHIVE_TREE_FOLDERS = [
        { type: "Gas Safety Certificate", label: "Gas Safety" },
        { type: "EICR", label: "EICR" },
        { type: "EPC", label: "EPC" },
        { type: "Deposit Protection Certificate", label: "Deposit" },
        { type: "Tenancy Agreement", label: "Tenancy Agreement" },
        { type: "Other", label: "Other" },
    ];
    let archiveExpandedPropertyIds = new Set();
    /** "__all__" | doc type key matching documents_by_type */
    let archiveSelectedFolderType = null;
    let archiveCurrentDetail = null;
    /** Main archive workspace: property documents table vs critical expiries list */
    let archiveWorkspaceMode = "documents";

    // ── State (property & compliance views) ─────────────────────────────────
    let currentPropertyId = null;
    let uploadModalApiRef = null;
    let propertyDetail = null;
    let propertyDocuments = [];
    let selectedDocId = null;

    /** Compliance page (luminous): workspace pane, list filters, selected action row */
    let complianceWorkspaceMode = "health";
    let complianceSelectedKey = "";
    let complianceTypeFilter = "all";
    let complianceSeverityFilter = "all";

    // ── State (chat / conversations sidebar) ─────────────────────────────────
    const CHAT_HISTORY_KEY = "morphiq_chat_history";
    const CONVERSATIONS_KEY = "morphiq_conversations";
    const CHAT_OPEN_KEY = "morphiq_chat_open";
    const CHAT_HISTORY_MAX = 50;
    let chatMessages = [];
    let chatRequestInFlight = false;
    let chatSidebarOpen = false;
    let chatHasUnreadSinceMinimize = false;
    /** Current conversation id when in chat view; null when on list view */
    let currentConversationId = null;
    /** Client name for chat POST; set from MORPHIQ_* / URL / property detail API */
    let chatClientName = "";

    /**
     * Append ?client= or &client= for admin-scoped API calls.
     * Prefer the URL bar (?client=); if missing, use MORPHIQ_PORTAL.clientName (e.g. document viewer
     * rendered with the document's client but no query string).
     */
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

    function getConversations() {
        try {
            const raw = localStorage.getItem(CONVERSATIONS_KEY);
            const arr = raw ? JSON.parse(raw) : [];
            return Array.isArray(arr) ? arr : [];
        } catch (_) {
            return [];
        }
    }

    function saveConversations(conversations) {
        try {
            localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(conversations));
        } catch (_) {}
    }

    /** Migrate legacy morphiq_chat_history into one conversation in morphiq_conversations */
    function migrateChatHistoryToConversations() {
        try {
            if (localStorage.getItem(CONVERSATIONS_KEY)) return;
            const raw = localStorage.getItem(CHAT_HISTORY_KEY);
            const arr = raw ? JSON.parse(raw) : [];
            if (!Array.isArray(arr) || arr.length === 0) return;
            const pairs = [];
            for (let i = 0; i < arr.length; i += 2) {
                const userItem = arr[i];
                const assistantItem = i + 1 < arr.length ? arr[i + 1] : null;
                if (!userItem || userItem.role !== "user") break;
                const userTime = (userItem.time || "").slice(0, 5) || "00:00";
                const assistantTime = (assistantItem && assistantItem.role === "assistant")
                    ? ((assistantItem.time || "").slice(0, 5) || userTime)
                    : userTime;
                pairs.push({
                    user: userItem.text || "",
                    assistant: (assistantItem && assistantItem.role === "assistant") ? (assistantItem.text || "") : "",
                    isError: false,
                    timestamp: "2000-01-01T" + userTime + ":00.000Z",
                    assistantTimestamp: "2000-01-01T" + assistantTime + ":00.000Z",
                });
            }
            if (pairs.length === 0) return;
            const firstUser = (pairs[0].user || "").trim();
            const title = firstUser.length > 40 ? firstUser.slice(0, 37) + "…" : firstUser || "Previous conversation";
            const now = new Date().toISOString();
            const conv = {
                id: "migrated-" + Date.now(),
                title: title,
                messages: pairs.slice(-CHAT_HISTORY_MAX),
                created_at: now,
                updated_at: now,
            };
            saveConversations([conv]);
        } catch (_) {}
    }

    function downloadReportPdf(url, button, defaultLabel) {
        if (!button) return;
        const originalText = button.textContent;
        button.textContent = "Generating...";
        button.disabled = true;
        fetch(url, { credentials: "include" })
            .then((res) => {
                if (!res.ok) return res.json().then((data) => Promise.reject(new Error((data && data.error) || "Download failed")));
                return res.blob().then((blob) => ({ blob, res }));
            })
            .then(({ blob, res }) => {
                let filename = "report.pdf";
                const disp = res.headers.get("Content-Disposition");
                if (disp) {
                    const match = disp.match(/filename\*?=(?:UTF-8'')?["']?([^"';]+)["']?/i) || disp.match(/filename=["']?([^"';]+)["']?/i);
                    if (match && match[1]) filename = match[1].trim();
                }
                const u = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = u;
                a.download = filename;
                a.click();
                URL.revokeObjectURL(u);
            })
            .catch((err) => {
                console.error("Report download failed:", err);
                alert(err.message || "Failed to generate report.");
            })
            .finally(() => {
                button.textContent = defaultLabel != null ? defaultLabel : originalText;
                button.disabled = false;
            });
    }

    // ── DOM refs (populated on init) ────────────────────────────────────────
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    // ── Icons ───────────────────────────────────────────────────────────────
    const DOC_ICONS = {
        "Tenancy Agreement": "📄",
        "Gas Safety Certificate": "🔥",
        "EICR": "⚡",
        "EPC": "🏠",
        "Deposit Protection": "🛡️",
        "Inventory": "📋",
    };
    const PROPERTY_ICON = "🏠";

    // ── Formatting helpers ──────────────────────────────────────────────────
    function statusClass(status) {
        if (!status) return "status-new";
        const s = status.toLowerCase().replace(/\s+/g, "-");
        const map = {
            "verified": "status-verified",
            "corrected-verified": "status-verified",
            "corrected_verified": "status-verified",
            "active": "status-active",
            "needs-review": "status-needs-review",
            "needs_review": "status-needs-review",
            "reported-under-review": "status-needs-review",
            "reported_under_review": "status-needs-review",
            "new": "status-new",
            "closed": "status-active",
            "failed": "status-failed",
            "expiring-soon": "status-expiring",
            "expiring": "status-expiring",
        };
        return map[s] || "status-new";
    }

    function statusLabel(status) {
        if (!status) return "New";
        const s = String(status).toLowerCase();
        const labels = {
            reported_under_review: "Under Review",
            corrected_verified: "Corrected & Verified",
        };
        if (labels[s]) return labels[s];
        return status.replace(/[_-]/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    }

    function formatDate(dateStr) {
        if (!dateStr) return "—";
        // Handle ISO and common formats
        const d = new Date(dateStr);
        if (isNaN(d)) return dateStr;
        return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
    }

    function complianceClass(status) {
        if (!status) return "pill-missing";
        const s = status.toLowerCase();
        if (s === "valid") return "pill-valid";
        if (s === "expiring_soon") return "pill-expiring-soon";
        if (s === "expired") return "pill-expired";
        return "pill-missing";
    }

    function complianceLabel(status) {
        if (!status) return "Missing";
        return status.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    }

    function docIcon(docType) {
        return DOC_ICONS[docType] || "📄";
    }

    function fieldLabel(key) {
        return key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    }

    // ── Search dropdown (API + recent) ────────────────────────────────────────
    const SEARCH_DROPDOWN_DEBOUNCE_MS = 300;
    const SEARCH_API_LIMIT = 8;
    const RECENT_SEARCHES_KEY = "morphiq_recent_searches";
    const RECENT_SEARCHES_MAX = 5;
    let searchDropdownDebounce = null;
    let searchDropdownEl = null;

    function getRecentSearches() {
        try {
            const raw = localStorage.getItem(RECENT_SEARCHES_KEY);
            const arr = raw ? JSON.parse(raw) : [];
            return Array.isArray(arr) ? arr.slice(0, RECENT_SEARCHES_MAX) : [];
        } catch (_) {
            return [];
        }
    }

    function saveRecentSearch(query) {
        const q = (query || "").trim();
        if (!q) return;
        let arr = getRecentSearches();
        arr = [q].concat(arr.filter((item) => item !== q)).slice(0, RECENT_SEARCHES_MAX);
        try {
            localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(arr));
        } catch (_) {}
    }

    function closeSearchDropdown() {
        if (searchDropdownEl) {
            searchDropdownEl.classList.remove("is-open");
            searchDropdownEl.innerHTML = "";
        }
    }

    function showSearchDropdown(html) {
        if (!searchDropdownEl) return;
        searchDropdownEl.innerHTML = html;
        searchDropdownEl.classList.add("is-open");
    }

    async function fetchSearchDocuments(query) {
        const q = encodeURIComponent((query || "").trim());
        if (!q) return [];
        const url = withClientQuery(`/api/documents?q=${q}&limit=${SEARCH_API_LIMIT}`);
        try {
            const res = await fetch(url, { credentials: "same-origin" });
            const data = await res.json();
            return data.documents || [];
        } catch (err) {
            console.error("Search API error:", err);
            return [];
        }
    }

    function renderSearchResults(docs) {
        if (!docs.length) {
            return `<div class="search-dropdown-empty">No documents found</div>`;
        }
        const dateField = (d) => d.scanned_at || d.imported_at || d.batch_date || "";
        return docs
            .map((d) => {
                const propId = d.property_id != null ? d.property_id : "";
                const focusSlug = (d.doc_type_slug || "").trim();
                const client = new URLSearchParams(window.location.search).get("client");
                const params = [];
                if (client) params.push("client=" + encodeURIComponent(client));
                if (focusSlug) params.push("focus=" + encodeURIComponent(focusSlug));
                const queryString = params.length ? "?" + params.join("&") : "";
                const url = propId ? `/property/${propId}${queryString}` : "#";
                const typeLabel = d.doc_type || "Document";
                const address = d.property_address || "—";
                const date = formatDate(dateField(d));
                const status = d.status || "";
                const badgeClass = statusClass(status);
                const badgeText = statusLabel(status);
                return `
                    <a class="search-dropdown-row" href="${url}" data-property-id="${propId}" data-doc-type="${focusSlug}">
                        <div class="search-dropdown-row-main">
                            <span class="search-dropdown-icon">${docIcon(typeLabel)}</span>
                            <div class="search-dropdown-row-text">
                                <span class="search-dropdown-type">${typeLabel}</span>
                                <span class="search-dropdown-date">${date}</span>
                            </div>
                            <span class="search-dropdown-address">${address}</span>
                        </div>
                        <span class="status-badge ${badgeClass}"><span class="dot"></span>${badgeText}</span>
                    </a>`;
            })
            .join("");
    }

    function renderRecentSearches(recent) {
        if (!recent.length) return "";
        const items = recent
            .map((q) => `<a class="search-dropdown-row search-dropdown-row-recent" href="#" data-recent-query="${q.replace(/"/g, "&quot;")}">${q}</a>`)
            .join("");
        return `
            <div class="search-dropdown-section-header">
                <span class="search-dropdown-label">Recent</span>
                <a href="#" class="search-dropdown-clear">Clear</a>
            </div>
            <div class="search-dropdown-items">${items}</div>`;
    }

    function initSearchDropdown() {
        const container = $(".search-container");
        const input = $(".search-input");
        if (!container || !input) return;

        if (!searchDropdownEl) {
            searchDropdownEl = document.createElement("div");
            searchDropdownEl.className = "search-dropdown";
            searchDropdownEl.setAttribute("id", "search-dropdown");
            container.appendChild(searchDropdownEl);
        }

        input.addEventListener("input", () => {
            const val = (input.value || "").trim();
            if (val.length >= 2) {
                clearTimeout(searchDropdownDebounce);
                searchDropdownDebounce = setTimeout(async () => {
                    const docs = await fetchSearchDocuments(val);
                    const html = renderSearchResults(docs);
                    showSearchDropdown(html);
                    bindSearchDropdownClicks();
                }, SEARCH_DROPDOWN_DEBOUNCE_MS);
            } else {
                if (searchDropdownEl && searchDropdownEl.classList.contains("is-open")) {
                    if (val.length === 0 && document.activeElement === input) {
                        const recent = getRecentSearches();
                        if (recent.length) {
                            showSearchDropdown(renderRecentSearches(recent));
                            bindSearchDropdownClicks();
                        } else {
                            closeSearchDropdown();
                        }
                    } else {
                        closeSearchDropdown();
                    }
                }
            }
        });

        input.addEventListener("focus", () => {
            const val = (input.value || "").trim();
            if (val.length === 0) {
                const recent = getRecentSearches();
                if (recent.length) {
                    showSearchDropdown(renderRecentSearches(recent));
                    bindSearchDropdownClicks();
                }
            }
        });

        input.addEventListener("keydown", (e) => {
            if (e.key === "Escape") {
                closeSearchDropdown();
                input.blur();
            }
        });

        document.addEventListener("click", (e) => {
            if (!searchDropdownEl || !searchDropdownEl.classList.contains("is-open")) return;
            if (!container.contains(e.target)) {
                closeSearchDropdown();
            }
        });

        function bindSearchDropdownClicks() {
            if (!searchDropdownEl) return;
            searchDropdownEl.querySelectorAll(".search-dropdown-row").forEach((row) => {
                row.addEventListener("click", (e) => {
                    const recentQuery = row.getAttribute("data-recent-query");
                    if (recentQuery != null) {
                        e.preventDefault();
                        input.value = recentQuery;
                        input.focus();
                        closeSearchDropdown();
                        input.dispatchEvent(new Event("input", { bubbles: true }));
                        return;
                    }
                    const query = (input.value || "").trim();
                    if (query) saveRecentSearch(query);
                });
            });
            const clearBtn = searchDropdownEl.querySelector(".search-dropdown-clear");
            if (clearBtn) {
                clearBtn.addEventListener("click", (e) => {
                    e.preventDefault();
                    try {
                        localStorage.setItem(RECENT_SEARCHES_KEY, "[]");
                    } catch (_) {}
                    closeSearchDropdown();
                });
            }
        }
    }

    // ── Client picker (no ?client) ───────────────────────────────────────────
    async function fetchClientsForPicker() {
        const statusEl = document.getElementById("client-picker-status");
        try {
            const res = await fetch("/api/clients");
            if (!res.ok) {
                throw new Error("Failed to load clients");
            }
            const data = await res.json();
            const clients = data.clients || [];
            renderClientPicker(clients);
            if (statusEl) {
                if (!clients.length) {
                    statusEl.textContent = "No active clients found in the portal database.";
                } else {
                    statusEl.textContent = `${clients.length} active client${clients.length === 1 ? "" : "s"} available.`;
                }
                statusEl.classList.remove("error");
            }
        } catch (err) {
            console.error("Failed to fetch clients:", err);
            if (statusEl) {
                statusEl.textContent = "Unable to load clients. Is the portal database available?";
                statusEl.classList.add("error");
            }
        }
    }

    function renderClientPicker(clients) {
        const grid = document.getElementById("client-grid");
        if (!grid) return;

        if (!clients.length) {
            grid.innerHTML = "";
            return;
        }

        grid.innerHTML = clients.map((c) => {
            const id = c.id;
            const name = c.name || "";
            const initial = name ? name.charAt(0).toUpperCase() : "?";
            return `
                <button class="client-card" type="button" data-client-id="${id}" data-client-name="${encodeURIComponent(name)}" title="${name}">
                    <div class="client-card-initial">${initial}</div>
                    <div class="client-card-content">
                        <div class="client-card-name">${name}</div>
                        <div class="client-card-meta">Open archive for this client</div>
                    </div>
                    <button type="button" class="client-delete-btn" title="Remove from portal">×</button>
                </button>
            `;
        }).join("");

        grid.querySelectorAll(".client-card").forEach((el) => {
            const encoded = el.getAttribute("data-client-name") || "";
            if (encoded) {
                el.addEventListener("click", () => {
                    window.location.href = `/overview?client=${encoded}`;
                });
            }

            const deleteBtn = el.querySelector(".client-delete-btn");
            if (deleteBtn) {
                deleteBtn.addEventListener("click", async (e) => {
                    e.stopPropagation();
                    const idAttr = el.getAttribute("data-client-id");
                    const rawName = decodeURIComponent(encoded || "");
                    const clientId = parseInt(idAttr || "", 10);
                    if (!idAttr || Number.isNaN(clientId)) return;

                    const ok = window.confirm(
                        `Delete "${rawName}" from the portal?\n\nThis removes all their data from the portal database.\nFiles on disk are NOT affected.`
                    );
                    if (!ok) return;

                    try {
                        const res = await fetch(`/api/clients/${clientId}`, { method: "DELETE" });
                        const data = await res.json().catch(() => ({}));
                        if (!res.ok || !data.success) {
                            const msg = (data && data.error) || `Delete failed with status ${res.status}`;
                            alert(msg);
                            return;
                        }
                        // Remove card from DOM
                        el.remove();
                    } catch (err) {
                        alert("Delete failed: " + (err && err.message ? err.message : String(err)));
                    }
                });
            }
        });
    }

    // ── Left-panel address parsing helpers (Archive tab) ────────────────
    // NOTE: property_address comes from the backend and may contain street + town + postcode.
    // We extract:
    // - postcode outward prefix (e.g. CM18) from the end of the address
    // - area/town name from the substring immediately before the postcode
    function normalizeAreaKey(area) {
        return (area || "").trim().toLowerCase();
    }

    function extractPostcodePrefixFromAddress(address) {
        const addr = (address || "").toString();
        // Outward: 1-2 letters + 1-2 digits + optional letter/digit suffix (e.g. CM18, EN11, SG13A)
        // Inward: digit + 2 letters (e.g. 3CH)
        const re = /([A-Z]{1,2}\d[A-Z\d]?)\s*(\d[A-Z]{2})$/i;
        const match = addr.match(re);
        if (!match) return "";
        return (match[1] || "").toUpperCase();
    }

    function extractAreaFromAddress(address) {
        const addr = (address || "").toString();
        const re = /([A-Z]{1,2}\d[A-Z\d]?)\s*(\d[A-Z]{2})$/i;
        const match = addr.match(re);
        if (!match) return "";

        const postcodeStart = typeof match.index === "number" ? match.index : (addr.length - match[0].length);
        const before = addr.slice(0, postcodeStart).trim();
        const cleaned = before.replace(/[,–—-]+\s*$/g, "").trim();

        // Prefer the last comma-separated segment (common format: "street, Town, POSTCODE")
        if (cleaned.includes(",")) {
            const parts = cleaned.split(",").map(s => s.trim()).filter(Boolean);
            if (parts.length) return parts[parts.length - 1];
        }

        // Fallback: last "wordy" chunk before postcode
        const m2 = cleaned.match(/([A-Za-z][A-Za-z\s'-]*)$/);
        return (m2 && m2[1]) ? m2[1].trim() : "";
    }

    function precomputeArchiveAddressParts(props) {
        (props || []).forEach((p) => {
            const address = p && p.property_address ? p.property_address : "";
            const areaLabel = extractAreaFromAddress(address);
            const areaKey = areaLabel ? normalizeAreaKey(areaLabel) : "";
            p.__archive_area_label = areaLabel || "";
            p.__archive_area_key = areaKey || "";
            p.__archive_postcode_prefix = extractPostcodePrefixFromAddress(address) || "";
        });
    }

    function refreshArchivePropertyListFiltersUI() {
        const areaSelect = document.querySelector("#archive-area-filter-select");
        const postcodeSelect = document.querySelector("#archive-postcode-filter-select");
        if (!areaSelect || !postcodeSelect) return;

        const areaMap = new Map(); // key -> label
        const postcodeSet = new Set();

        (allProperties || []).forEach((p) => {
            if (p && p.__archive_area_key) {
                if (!areaMap.has(p.__archive_area_key)) {
                    areaMap.set(p.__archive_area_key, p.__archive_area_label || p.__archive_area_key);
                }
            }
            if (p && p.__archive_postcode_prefix) {
                postcodeSet.add(p.__archive_postcode_prefix);
            }
        });

        const areas = Array.from(areaMap.entries())
            .sort((a, b) => (a[1] || "").localeCompare(b[1] || ""));
        const prefixes = Array.from(postcodeSet)
            .sort((a, b) => (a || "").localeCompare(b || ""));

        // Preserve existing selections if possible
        if (archiveAreaFilter && !areaMap.has(archiveAreaFilter)) archiveAreaFilter = "";
        if (archivePostcodePrefixFilter && !prefixes.includes(archivePostcodePrefixFilter)) {
            archivePostcodePrefixFilter = "";
        }

        // Build options without HTML injection (option.textContent)
        areaSelect.innerHTML = "";
        const allAreasOpt = document.createElement("option");
        allAreasOpt.value = "";
        allAreasOpt.textContent = "All areas";
        areaSelect.appendChild(allAreasOpt);
        areas.forEach(([key, label]) => {
            const opt = document.createElement("option");
            opt.value = key;
            opt.textContent = label;
            areaSelect.appendChild(opt);
        });

        postcodeSelect.innerHTML = "";
        const allPostcodesOpt = document.createElement("option");
        allPostcodesOpt.value = "";
        allPostcodesOpt.textContent = "All postcodes";
        postcodeSelect.appendChild(allPostcodesOpt);
        prefixes.forEach((prefix) => {
            const opt = document.createElement("option");
            opt.value = prefix;
            opt.textContent = prefix;
            postcodeSelect.appendChild(opt);
        });

        areaSelect.value = archiveAreaFilter || "";
        postcodeSelect.value = archivePostcodePrefixFilter || "";
    }

    function archiveFolderLabel(folderType) {
        if (!folderType || folderType === "__all__") return "All documents";
        const row = ARCHIVE_TREE_FOLDERS.find((f) => f.type === folderType);
        return row ? row.label : folderType;
    }

    function pickDefaultArchiveFolder(detail) {
        const byType = (detail && detail.documents_by_type) || {};
        for (let i = 0; i < ARCHIVE_TREE_FOLDERS.length; i++) {
            const t = ARCHIVE_TREE_FOLDERS[i].type;
            if ((byType[t] || []).length > 0) return t;
        }
        return "__all__";
    }

    function countDocsInFolder(detail, folderType) {
        if (!detail || !folderType || folderType === "__all__") {
            return (detail && detail.documents) ? detail.documents.length : 0;
        }
        const byType = detail.documents_by_type || {};
        return (byType[folderType] || []).length;
    }

    function getArchiveTableDocs(detail) {
        if (!detail) return [];
        const byType = detail.documents_by_type || {};
        let docs;
        if (!archiveSelectedFolderType || archiveSelectedFolderType === "__all__") {
            docs = (detail.documents || []).slice();
        } else {
            docs = (byType[archiveSelectedFolderType] || []).slice();
        }
        docs.sort((a, b) => {
            const aDate = a.scanned_at || a.imported_at || a.batch_date || "";
            const bDate = b.scanned_at || b.imported_at || b.batch_date || "";
            return (bDate || "").localeCompare(aDate || "");
        });
        return docs;
    }

    function archiveStatusPillText(status) {
        const s = (status || "").toLowerCase().replace(/\s+/g, "_");
        const map = {
            verified: "VERIFIED",
            new: "NEW",
            failed: "FAILED",
            needs_review: "NEEDS REVIEW",
            "needs-review": "NEEDS REVIEW",
            sent_to_rescan: "ACTION REQUIRED",
            reprocessing: "PROCESSING",
            ai_prefilled: "NEEDS REVIEW",
        };
        if (map[s]) return map[s];
        return statusLabel(status || "").toUpperCase();
    }

    function archiveStatusPillClass(status) {
        const s = (status || "").toLowerCase().replace(/\s+/g, "_");
        if (s === "verified") return "archive-pill-verified";
        if (s === "failed" || s === "sent_to_rescan") return "archive-pill-action";
        if (s === "needs_review" || s === "needs-review" || s === "ai_prefilled") return "archive-pill-review";
        if (s === "new" || s === "reprocessing") return "archive-pill-muted";
        return "archive-pill-muted";
    }

    function renderArchiveDocumentTableRows(docs) {
        if (!docs.length) {
            return `<tr><td colspan="5" class="archive-doc-table-empty">No documents in this folder.</td></tr>`;
        }
        return docs.map((doc) => {
            const name = (doc.doc_name || doc.doc_type || doc.source_doc_id || "Document").replace(/</g, "&lt;");
            const type = (doc.doc_type || "—").replace(/</g, "&lt;");
            const dateRaw = doc.scanned_at || doc.imported_at || doc.batch_date || doc.reviewed_at || "";
            const dateStr = dateRaw ? formatDate(dateRaw) : "—";
            const docId = (doc.source_doc_id || "").replace(/"/g, "&quot;");
            const dbIdAttr = doc.id != null ? String(doc.id).replace(/"/g, "&quot;") : "";
            const st = archiveStatusPillText(doc.status);
            const pillClass = archiveStatusPillClass(doc.status);
            return `
                <tr class="archive-doc-table-row" data-archive-doc-id="${docId}" data-doc-db-id="${dbIdAttr}">
                    <td class="archive-doc-col-name">
                        <button type="button" class="archive-doc-name-btn" data-archive-doc-id="${docId}" data-doc-db-id="${dbIdAttr}">
                            <span class="archive-doc-type-icon">${docIcon(doc.doc_type)}</span>
                            <span class="archive-doc-name-text">${name}</span>
                        </button>
                    </td>
                    <td class="archive-doc-col-type">${type}</td>
                    <td class="archive-doc-col-date">${dateStr}</td>
                    <td class="archive-doc-col-size">—</td>
                    <td class="archive-doc-col-status">
                        <span class="archive-status-pill ${pillClass}">${st}</span>
                    </td>
                </tr>`;
        }).join("");
    }

    function renderArchiveDocumentViewHTML(detail) {
        const address = (detail.property_address || "Property").replace(/</g, "&lt;");
        const folderLabel = archiveFolderLabel(archiveSelectedFolderType);
        const docs = getArchiveTableDocs(detail);
        const rows = renderArchiveDocumentTableRows(docs);

        return `
            <div class="archive-main-panel">
                <div class="archive-main-toolbar">
                    <nav class="archive-breadcrumb" aria-label="Breadcrumb">
                        <span class="archive-crumb">Portfolio</span>
                        <span class="archive-crumb-sep">›</span>
                        <span class="archive-crumb">${address}</span>
                        <span class="archive-crumb-sep">›</span>
                        <span class="archive-crumb archive-crumb-active">${folderLabel.replace(/</g, "&lt;")}</span>
                    </nav>
                    <div class="archive-main-actions">
                        <button type="button" class="archive-toolbar-btn" id="archive-main-export-btn" title="Export compliance report">Export</button>
                        <button type="button" class="archive-toolbar-btn" id="archive-main-filter-btn" title="Scroll to filters">Filter</button>
                    </div>
                </div>
                <div class="archive-doc-table-wrap">
                    <table class="archive-doc-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Type</th>
                                <th>Date modified</th>
                                <th>Size</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows}
                        </tbody>
                    </table>
                </div>
            </div>`;
    }

    function bindArchiveMainPanelEvents(detailRoot) {
        if (!detailRoot) return;
        detailRoot.querySelectorAll(".archive-doc-name-btn[data-archive-doc-id]").forEach((btn) => {
            btn.addEventListener("click", (ev) => {
                const id = btn.getAttribute("data-archive-doc-id");
                const dbId = btn.getAttribute("data-doc-db-id") || "";
                if (id) openArchiveDocumentFromTable(id, dbId, ev);
                updateArchiveStatusBar();
            });
        });
        const exp = detailRoot.querySelector("#archive-main-export-btn");
        if (exp && !exp.dataset.bound) {
            exp.addEventListener("click", () => {
                const top = document.querySelector("#dashboard-export-report");
                if (top) top.click();
            });
            exp.dataset.bound = "1";
        }
        const filt = detailRoot.querySelector("#archive-main-filter-btn");
        if (filt && !filt.dataset.bound) {
            filt.addEventListener("click", () => {
                const bar = document.querySelector("#dashboard-archive .filter-bar");
                if (bar) bar.scrollIntoView({ behavior: "smooth", block: "start" });
            });
            filt.dataset.bound = "1";
        }
    }

    function updateArchiveStatusBar() {
        const bar = document.getElementById("archive-status-bar");
        const itemsEl = document.getElementById("archive-status-items");
        const selEl = document.getElementById("archive-status-selected");
        if (!bar || !itemsEl || !selEl) return;
        const n = archiveCurrentDetail ? getArchiveTableDocs(archiveCurrentDetail).length : 0;
        const sel = selectedDocId ? 1 : 0;
        itemsEl.textContent = `${n} item${n !== 1 ? "s" : ""}`;
        selEl.textContent = `${sel} selected`;
        bar.hidden = !archiveCurrentDetail;
    }

    // ── API (archive view) ─────────────────────────────────────────────────
    async function fetchProperties() {
        try {
            const baseUrl = "/api/properties";
            const clientName = (window.MORPHIQ_PORTAL && window.MORPHIQ_PORTAL.clientName) || "";
            const url = clientName ? `${baseUrl}?client=${encodeURIComponent(clientName)}` : baseUrl;
            const res = await fetch(url);
            const data = await res.json();
            allProperties = data.properties || [];
            precomputeArchiveAddressParts(allProperties);
            refreshArchivePropertyListFiltersUI();
            applyFilters();
            updateStats();
        } catch (err) {
            console.error("Failed to fetch properties:", err);
            showEmptyState("Failed to load properties. Is the server running?");
        }
    }

    // ── Filter & Search (archive view) ─────────────────────────────────────-
    function applyFilters() {
        let props = [...allProperties];

        // Compliance filter
        if (activeFilter !== "all") {
            props = props.filter((p) => {
                const status = (p[activeFilter] || "").toLowerCase();
                return status && status !== "missing";
            });
        }

        // Status filter (any type matching selected status)
        if (archiveStatusFilter !== "all") {
            const target = archiveStatusFilter;
            props = props.filter((p) => {
                const statuses = [
                    (p.gas_safety || "").toLowerCase(),
                    (p.eicr || "").toLowerCase(),
                    (p.epc || "").toLowerCase(),
                    (p.deposit || "").toLowerCase(),
                ];
                return statuses.includes(target);
            });
        }

        // Search
        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            props = props.filter(p =>
                (p.property_address || "").toLowerCase().includes(q) ||
                (p.client_name || "").toLowerCase().includes(q)
            );
        }

        // Sort
        props.sort((a, b) => {
            switch (currentSort) {
                case "newest":
                    return (b.latest_activity_date || "").localeCompare(a.latest_activity_date || "");
                case "name":
                    return (a.property_address || "").localeCompare(b.property_address || "");
                case "documents":
                    return (b.total_documents || 0) - (a.total_documents || 0);
                case "health": {
                    const healthPct = (p) => Math.round((STATUS_KEYS.filter((k) => (p[k] || "").toLowerCase() === "valid").length / 4) * 100);
                    return healthPct(a) - healthPct(b);
                }
                default:
                    return 0;
            }
        });

        filteredProperties = props;
        renderPropertyList();
        updateSearchCount();
    }

    // ── Stats (archive view) — portfolio compliance from allProperties ────────
    const STATUS_KEYS = ["gas_safety", "eicr", "epc", "deposit"];

    function updateStats() {
        const total = allProperties.length;

        let fullyCompliant = 0;
        let expiringSoon = 0;
        let nonCompliant = 0;

        allProperties.forEach((p) => {
            const statuses = STATUS_KEYS.map((k) => (p[k] || "").toLowerCase());
            const allValid = statuses.every((s) => s === "valid");
            const anyExpiring = statuses.some((s) => s === "expiring_soon");
            const anyBad = statuses.some((s) => s === "expired" || s === "missing");

            if (allValid) fullyCompliant += 1;
            if (anyExpiring) expiringSoon += 1;
            if (anyBad) nonCompliant += 1;
        });

        const pct = total > 0 ? Math.round((fullyCompliant / total) * 100) : 0;

        const statTotalEl = $("#stat-total-props");
        const statCompliantEl = $("#stat-compliant");
        const statExpiringEl = $("#stat-expiring");
        const statNoncompliantEl = $("#stat-noncompliant");

        if (statTotalEl) {
            const val = statTotalEl.querySelector(".stat-value");
            if (val) val.textContent = total;
        }
        if (statCompliantEl) {
            const val = statCompliantEl.querySelector(".stat-value");
            const sub = statCompliantEl.querySelector(".stat-sub");
            if (val) val.textContent = fullyCompliant;
            if (sub) sub.textContent = total > 0 ? `${pct}% of portfolio` : "—";
        }
        if (statExpiringEl) {
            const val = statExpiringEl.querySelector(".stat-value");
            const sub = statExpiringEl.querySelector(".stat-sub");
            if (val) val.textContent = expiringSoon;
            if (sub) sub.textContent = expiringSoon ? "in next 30 days" : "—";
        }
        if (statNoncompliantEl) {
            const val = statNoncompliantEl.querySelector(".stat-value");
            const sub = statNoncompliantEl.querySelector(".stat-sub");
            if (val) val.textContent = nonCompliant;
            const exposure = nonCompliant ? nonCompliant * 6000 : 0;
            if (sub) sub.innerHTML = nonCompliant ? `Est. exposure: £${exposure.toLocaleString()}` : "—";
        }

        // Show/hide 0% compliance banner above table
        const banner = $("#compliance-empty-banner");
        const bannerLink = $("#compliance-empty-banner-link");
        const showBanner = total > 0 && fullyCompliant === 0;
        if (banner) banner.style.display = showBanner ? "flex" : "none";
        if (bannerLink && showBanner) {
            const firstProp = allProperties[0];
            if (firstProp && firstProp.property_id) {
                const clientName = (window.MORPHIQ_PORTAL && window.MORPHIQ_PORTAL.clientName) || "";
                const qs = clientName ? "?client=" + encodeURIComponent(clientName) : "";
                bannerLink.href = "/property/" + firstProp.property_id + qs;
            } else {
                bannerLink.href = "#";
            }
        }
    }

    function updateSearchCount() {
        const el = $("#search-count");
        if (!el) return;
        if (searchQuery) {
            el.textContent = `${filteredProperties.length} result${filteredProperties.length !== 1 ? "s" : ""}`;
            el.style.display = "block";
        } else {
            el.style.display = "none";
        }
    }

    // ── Render property tree (archive view, left panel) ──────────────────────
    function renderPropertyList() {
        const listEl = $("#archive-property-list");
        if (!listEl) return;

        // Start from globally filtered properties, then apply left-panel search
        let props = [...filteredProperties];
        if (listSearchQuery) {
            const q = listSearchQuery.toLowerCase();
            props = props.filter((p) =>
                (p.property_address || "").toLowerCase().includes(q)
            );
        }

        // Left-panel dropdown filters (AND logic with list search)
        if (archiveAreaFilter) {
            props = props.filter((p) => (p.__archive_area_key || "") === archiveAreaFilter);
        }
        if (archivePostcodePrefixFilter) {
            props = props.filter((p) => (p.__archive_postcode_prefix || "") === archivePostcodePrefixFilter);
        }

        // If current selection is filtered out, clear selection and reset detail panel
        if (
            selectedPropertyId != null &&
            !props.some((p) => p.property_id === selectedPropertyId)
        ) {
            selectedPropertyId = null;
            archiveExpandedPropertyIds.clear();
            archiveCurrentDetail = null;
            archiveSelectedFolderType = null;
            selectedDocId = null;
            const detailRoot = $("#archive-property-detail");
            if (detailRoot) {
                detailRoot.innerHTML = `
                    <div class="archive-detail-empty">
                        <div class="archive-detail-empty-icon">📂</div>
                        <div class="archive-detail-empty-title">Select a property</div>
                        <div class="archive-detail-empty-upload">
                            <span class="archive-detail-empty-text">Expand an address and choose a folder to browse documents.</span>
                        </div>
                    </div>
                `;
            }
            updateArchiveStatusBar();
        }

        if (props.length === 0) {
            const hasAnyListFilter = !!(searchQuery || listSearchQuery || archiveAreaFilter || archivePostcodePrefixFilter);
            listEl.innerHTML = `<div class="empty-state">` +
                (hasAnyListFilter ? "No properties match your filters." : "No properties found.") +
                `</div>`;
            return;
        }

        listEl.innerHTML = props.map((prop) => {
            const pid = prop.property_id;
            const isPropertySelected = pid === selectedPropertyId;
            const expanded = archiveExpandedPropertyIds.has(pid);
            const statuses = STATUS_KEYS.map((k) => (prop[k] || "").toLowerCase());
            const validCount = statuses.filter((s) => s === "valid").length;
            const healthPct = Math.round((validCount / 4) * 100);
            let healthClass = "archive-tree-health-low";
            if (healthPct > 74) healthClass = "archive-tree-health-high";
            else if (healthPct > 25) healthClass = "archive-tree-health-mid";

            const addr = (prop.property_address || "Unnamed property").replace(/</g, "&lt;");
            const docCount = prop.total_documents || 0;

            const foldersHtml = ARCHIVE_TREE_FOLDERS.map(({ type, label }) => {
                const count = (isPropertySelected && archiveCurrentDetail && archiveCurrentDetail.property_id === pid)
                    ? countDocsInFolder(archiveCurrentDetail, type)
                    : null;
                const countStr = count != null ? ` (${count})` : "";
                const isFolderActive = isPropertySelected && archiveSelectedFolderType === type;
                return `
                    <button type="button" class="archive-tree-folder${isFolderActive ? " active" : ""}"
                        data-property-id="${pid}" data-archive-folder="${type.replace(/"/g, "&quot;")}">
                        <span class="archive-tree-folder-dot"></span>
                        <span class="archive-tree-folder-label">${label}${countStr}</span>
                    </button>`;
            }).join("");

            const allActive = isPropertySelected && archiveSelectedFolderType === "__all__";
            const allCount = (isPropertySelected && archiveCurrentDetail && archiveCurrentDetail.property_id === pid)
                ? countDocsInFolder(archiveCurrentDetail, "__all__")
                : null;
            const allCountStr = allCount != null ? ` (${allCount})` : "";

            return `
                <div class="archive-tree-property${isPropertySelected ? " is-property-selected" : ""}" data-property-id="${pid}">
                    <button type="button" class="archive-tree-property-header">
                        <span class="archive-tree-chevron" aria-hidden="true">${expanded ? "▾" : "▸"}</span>
                        <span class="archive-tree-folder-ico" aria-hidden="true">📁</span>
                        <span class="archive-tree-property-info">
                            <span class="archive-tree-address">${addr}</span>
                            <span class="archive-tree-meta">${docCount} doc${docCount === 1 ? "" : "s"}</span>
                        </span>
                        <span class="archive-tree-health ${healthClass}">${healthPct}%</span>
                    </button>
                    <div class="archive-tree-children" style="display:${expanded ? "block" : "none"}">
                        ${foldersHtml}
                        <button type="button" class="archive-tree-folder archive-tree-folder-all${allActive ? " active" : ""}"
                            data-property-id="${pid}" data-archive-folder="__all__">
                            <span class="archive-tree-folder-dot"></span>
                            <span class="archive-tree-folder-label">All documents${allCountStr}</span>
                        </button>
                    </div>
                </div>`;
        }).join("");

        listEl.querySelectorAll(".archive-tree-property-header").forEach((header) => {
            header.addEventListener("click", (e) => {
                e.preventDefault();
                const wrap = header.closest(".archive-tree-property");
                if (!wrap) return;
                const pid = parseInt(wrap.getAttribute("data-property-id") || "", 10);
                if (Number.isNaN(pid)) return;

                if (selectedPropertyId === pid) {
                    if (archiveExpandedPropertyIds.has(pid)) archiveExpandedPropertyIds.delete(pid);
                    else archiveExpandedPropertyIds.add(pid);
                    renderPropertyList();
                    return;
                }

                selectedPropertyId = pid;
                archiveExpandedPropertyIds.clear();
                archiveExpandedPropertyIds.add(pid);
                archiveSelectedFolderType = null;
                archiveCurrentDetail = null;
                selectedDocId = null;
                renderPropertyList();
                loadPropertyDetail(pid);
            });
        });

        listEl.querySelectorAll(".archive-tree-folder[data-archive-folder]").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                e.stopPropagation();
                const pid = parseInt(btn.getAttribute("data-property-id") || "", 10);
                const folder = btn.getAttribute("data-archive-folder") || "__all__";
                if (Number.isNaN(pid)) return;

                selectedPropertyId = pid;
                archiveExpandedPropertyIds.add(pid);
                archiveSelectedFolderType = folder;
                selectedDocId = null;

                if (archiveCurrentDetail && archiveCurrentDetail.property_id === pid) {
                    propertyDocuments = archiveCurrentDetail.documents || [];
                    const detailRoot = $("#archive-property-detail");
                    if (detailRoot) {
                        detailRoot.innerHTML = renderArchiveDocumentViewHTML(archiveCurrentDetail);
                        bindArchiveMainPanelEvents(detailRoot);
                    }
                    updateArchiveStatusBar();
                    renderPropertyList();
                } else {
                    renderPropertyList();
                    loadPropertyDetail(pid);
                }
            });
        });
    }

    // ── Load property detail into right panel ───────────────────────────────
    async function loadPropertyDetail(propertyId) {
        const detailRoot = $("#archive-property-detail");
        if (!detailRoot || !propertyId) return;

        detailRoot.innerHTML = `<div class="loading-state">Loading property…</div>`;

        try {
            const detail = await fetchPropertyDetail(propertyId);
            if (!detail) {
                archiveCurrentDetail = null;
                detailRoot.innerHTML = `<div class="empty-state">Failed to load property details.</div>`;
                updateArchiveStatusBar();
                renderPropertyList();
                return;
            }

            archiveCurrentDetail = detail;
            propertyDocuments = detail.documents || [];

            if (archiveSelectedFolderType == null) {
                archiveSelectedFolderType = pickDefaultArchiveFolder(detail);
            }

            detailRoot.innerHTML = renderArchiveDocumentViewHTML(detail);
            bindArchiveMainPanelEvents(detailRoot);
            updateArchiveStatusBar();
            renderPropertyList();
        } catch (err) {
            console.error("Failed to load property detail:", err);
            archiveCurrentDetail = null;
            detailRoot.innerHTML = `<div class="empty-state">Unable to load property detail.</div>`;
            updateArchiveStatusBar();
        }
    }

    function showEmptyState(message) {
        const listEl = $("#archive-property-list");
        if (listEl) {
            listEl.innerHTML = `<div class="empty-state">${message}</div>`;
        }
    }

    // ── Critical Expiries (archive left panel; toggle from "All properties") ──
    function updateArchiveCriticalTabCount(n) {
        const tabCount = document.getElementById("archive-critical-tab-count");
        if (!tabCount) return;
        if (n > 0) {
            tabCount.textContent = " " + String(n);
            tabCount.hidden = false;
        } else {
            tabCount.textContent = "";
            tabCount.hidden = true;
        }
    }

    function setArchiveWorkspaceMode(mode) {
        const next = mode === "critical" ? "critical" : "documents";
        archiveWorkspaceMode = next;
        const docSec = document.getElementById("archive-workspace-documents");
        const critSec = document.getElementById("archive-workspace-critical");
        document.querySelectorAll(".archive-workspace-mode-toggle .archive-workspace-mode-btn").forEach((btn) => {
            const on = btn.getAttribute("data-workspace-mode") === next;
            btn.classList.toggle("active", on);
            btn.setAttribute("aria-selected", on ? "true" : "false");
        });
        if (docSec) {
            docSec.hidden = next !== "documents";
        }
        if (critSec) {
            critSec.hidden = next !== "critical";
        }
        if (next === "critical") {
            fetchCriticalExpiries();
        }
    }

    async function fetchCriticalExpiries() {
        const listEl = document.getElementById("archive-critical-list");

        if (!listEl) return;

        try {
            const clientName = (window.MORPHIQ_PORTAL && window.MORPHIQ_PORTAL.clientName) || "";
            const url = clientName
                ? `/api/compliance?client=${encodeURIComponent(clientName)}`
                : "/api/compliance";
            const res = await fetch(url);
            const data = await res.json();
            const actions = data.actions || [];
            const critical = actions.filter(
                (a) => (a.status || "") === "expired" || (a.status || "") === "expiring_soon"
            );
            renderCriticalExpiries(critical, listEl);
        } catch (err) {
            console.error("Failed to fetch critical expiries:", err);
            listEl.innerHTML = `<div class="critical-expiries-empty">Unable to load compliance data.</div>`;
            updateArchiveCriticalTabCount(0);
        }
    }

    function renderCriticalExpiries(critical, listEl) {
        if (!listEl) return;

        updateArchiveCriticalTabCount(critical.length);

        if (!critical.length) {
            listEl.innerHTML = `<div class="empty-state">No critical expiries</div>`;
            return;
        }

        const clientName = (window.MORPHIQ_PORTAL && window.MORPHIQ_PORTAL.clientName) || "";

        const FOCUS_SLUGS = { gas_safety: "gas-safety-certificate", eicr: "eicr", epc: "epc", deposit: "deposit-protection" };
        listEl.innerHTML = critical
            .map((a) => {
                const isExpired = (a.status || "") === "expired";
                const typeSlug = FOCUS_SLUGS[(a.type || "").trim()] || "";
                let viewHref = a.property_id ? `/property/${a.property_id}` : "#";
                if (a.property_id && typeSlug) {
                    const params = ["focus=" + encodeURIComponent(typeSlug)];
                    if (clientName) params.push("client=" + encodeURIComponent(clientName));
                    viewHref = "/property/" + a.property_id + "?" + params.join("&");
                }
                const address = (a.property || "—") || "—";
                const badgeText = isExpired ? (a.badge_text || "Overdue") : (a.badge_text || "Expiring");
                const typeLabel = a.type_label || "Certificate";
                const pid = (a.property_id != null) ? String(a.property_id) : "";
                const ctype = (a.type || "").replace(/"/g, "&quot;");
                return `
                    <div class="critical-expiry-card-compact archive-critical-item" data-property-id="${pid}" data-comp-type="${ctype}">
                        <div class="archive-critical-item-main">
                            <span class="critical-expiry-badge ${isExpired ? "overdue" : "soon"}">${badgeText.replace(/</g, "&lt;")}</span>
                            <span class="critical-expiry-card-address">${address.replace(/</g, "&lt;")}</span>
                        </div>
                        <div class="critical-expiry-card-type">${typeLabel.replace(/</g, "&lt;")}</div>
                        <a class="critical-expiry-view-btn" href="${viewHref}">View</a>
                    </div>`;
            })
            .join("");

    }

    // ── Drawer helpers (shared) ─────────────────────────────────────────────
    function closeDrawer() {
        selectedDocId = null;
        const wrapper = $("#detail-drawer-wrapper");
        const drawer = $("#detail-drawer");
        if (wrapper) wrapper.classList.add("hidden");
        if (drawer) drawer.classList.add("hidden");
        $$(".doc-item").forEach(el => el.classList.remove("selected"));
        $$(".archive-doc-table-row").forEach((row) => row.classList.remove("selected"));
        updateArchiveStatusBar();
    }

    function buildArchiveDocumentUrl(sourceDocId, docDbId) {
        if (!sourceDocId) return "";
        const params = new URLSearchParams();
        const client =
            (window.MORPHIQ_PORTAL && window.MORPHIQ_PORTAL.clientName) ||
            new URLSearchParams(window.location.search).get("client");
        if (client) params.set("client", client);
        const qs = params.toString();
        const suffix = qs ? `?${qs}` : "";
        if (docDbId != null && String(docDbId).trim() !== "") {
            return `/document/by-id/${encodeURIComponent(docDbId)}${suffix}`;
        }
        return `/document/${encodeURIComponent(sourceDocId)}${suffix}`;
    }

    /** Same-tab navigation from Archive table; Ctrl/Cmd/Shift+click opens a new tab. */
    function openArchiveDocumentFromTable(sourceDocId, docDbId, ev) {
        const url = buildArchiveDocumentUrl(sourceDocId, docDbId);
        if (!url) return;
        if (ev && (ev.ctrlKey || ev.metaKey || ev.shiftKey)) {
            window.open(url, "_blank", "noopener,noreferrer");
            return;
        }
        window.location.assign(url);
    }

    function switchDrawerTab(tabName) {
        $$(".drawer-tab").forEach(tab => {
            tab.classList.toggle("active", tab.getAttribute("data-tab") === tabName);
        });
        $$(".tab-panel").forEach(panel => {
            panel.classList.toggle("active", panel.getAttribute("data-tab") === tabName);
        });
    }

    // ── Property detail view: API ───────────────────────────────────────────
    async function fetchPropertyDetail(propertyId) {
        const res = await fetch(withClientQuery(`/api/properties/${propertyId}`), {
            credentials: "same-origin",
        });
        if (!res.ok) {
            throw new Error(`Failed to load property ${propertyId}`);
        }
        const data = await res.json();
        return data.property || null;
    }

    async function fetchDocumentDetail(sourceDocId) {
        try {
            const res = await fetch(
                withClientQuery(`/api/documents/${encodeURIComponent(sourceDocId)}`),
                { credentials: "same-origin" }
            );
            if (!res.ok) return null;
            return await res.json();
        } catch (err) {
            console.error("Failed to fetch document detail:", err);
            return null;
        }
    }

    // ── Property detail view: rendering ─────────────────────────────────────
    const PROPERTY_COMPLIANCE_TYPES = [
        { key: "gas_safety", label: "Gas Safety", docType: "Gas Safety Certificate", sectionSlug: "gas-safety-certificate" },
        { key: "eicr", label: "EICR", docType: "EICR", sectionSlug: "eicr" },
        { key: "epc", label: "EPC", docType: "EPC", sectionSlug: "epc" },
        { key: "deposit", label: "Deposit", docType: "Deposit Protection Certificate", sectionSlug: "deposit-protection-certificate" },
    ];

    function renderPropertyHeader(detail) {
        const titleEl = $("#property-title");
        const metaEl = $("#property-meta");
        if (titleEl) titleEl.textContent = detail.property_address || "Property";
        if (!metaEl) return;
        const parts = [];
        if (detail.client_name) parts.push(detail.client_name);
        const tenant = detail.tenant;
        if (tenant && (tenant.name || tenant.tenant_name)) {
            parts.push((tenant.name || tenant.tenant_name).trim());
        }
        if (tenant && (tenant.tenancy_start || tenant.tenancy_end)) {
            const start = tenant.tenancy_start || "—";
            const end = tenant.tenancy_end || "—";
            parts.push(`${start} – ${end}`);
        }
        metaEl.textContent = parts.length ? parts.join(" · ") : "—";
    }

    function daysBetween(fromDate, toDate) {
        if (!fromDate || !toDate) return null;
        const from = new Date(fromDate);
        const to = new Date(toDate);
        if (isNaN(from) || isNaN(to)) return null;
        return Math.floor((to - from) / 86400000);
    }

    function renderComplianceSummary(detail) {
        const container = $("#property-compliance");
        if (!container) return;

        container.innerHTML = PROPERTY_COMPLIANCE_TYPES.map(({ key, label, docType, sectionSlug }) => {
            const info = detail[key] || {};
            const status = (info.status || "missing").toLowerCase();
            const expiryDate = info.expiry_date || null;
            const expiryStr = expiryDate ? formatDate(expiryDate) : "";
            const now = new Date();
            const expiry = expiryDate ? new Date(expiryDate) : null;
            const daysRemaining = expiry ? daysBetween(now, expiry) : null;
            const daysOverdue = expiry && daysRemaining !== null && daysRemaining < 0 ? Math.abs(daysRemaining) : null;

            let cardClass = "property-compliance-card property-compliance-card-" + status;
            let statusLabelText = complianceLabel(status);
            let bodyHtml = "";

            if (status === "expired") {
                bodyHtml = daysOverdue !== null
                    ? `<div class="property-compliance-expired">Expired ${daysOverdue} day${daysOverdue === 1 ? "" : "s"} ago</div><div class="property-compliance-liability">£6,000 liability</div>`
                    : `<div class="property-compliance-expired">Expired</div><div class="property-compliance-liability">£6,000 liability</div>`;
            } else if (status === "valid") {
                bodyHtml = `<span class="property-compliance-check">✓</span><span class="property-compliance-expires">Expires ${expiryStr || "—"}</span>`;
                if (daysRemaining !== null && daysRemaining >= 0) {
                    bodyHtml += `<div class="property-compliance-countdown">${daysRemaining} days left</div>`;
                }
            } else if (status === "expiring_soon") {
                bodyHtml = `<span class="property-compliance-expires">Expires ${expiryStr || "—"}</span>`;
                if (daysRemaining !== null) {
                    bodyHtml += `<div class="property-compliance-countdown">${daysRemaining} days left</div>`;
                }
            } else {
                bodyHtml = `<div class="property-compliance-missing-text">No certificate on file</div><button type="button" class="btn-compliance-upload" data-doc-type="${(docType || "").replace(/"/g, "&quot;")}">Upload</button>`;
            }

            const sectionId = "property-doc-group-" + sectionSlug;
            return `
                <button type="button" class="${cardClass}" data-scroll-to="${sectionId}">
                    <div class="property-compliance-card-label">${(label || "").replace(/</g, "&lt;")}</div>
                    <div class="property-compliance-card-status">${statusLabelText}</div>
                    <div class="property-compliance-card-body">${bodyHtml}</div>
                </button>
            `;
        }).join("");

        container.querySelectorAll(".property-compliance-card").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                if (e.target.classList.contains("btn-compliance-upload")) return;
                const id = btn.getAttribute("data-scroll-to");
                if (id) {
                    const el = document.getElementById(id);
                    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            });
        });
        container.querySelectorAll(".btn-compliance-upload").forEach((uploadBtn) => {
            uploadBtn.addEventListener("click", (e) => {
                e.preventDefault();
                e.stopPropagation();
                const docType = uploadBtn.getAttribute("data-doc-type");
                if (uploadModalApiRef) uploadModalApiRef.openUploadModal({ propertyId: currentPropertyId, docType: docType || undefined });
            });
        });
    }

    function docTypeToSectionSlug(type) {
        return (type || "").toLowerCase().replace(/\s+/g, "-");
    }

    function renderPropertyDocuments(detail) {
        const container = $("#property-doc-groups");
        if (!container) return;

        const byType = detail.documents_by_type || {};
        const typeOrder = ["Gas Safety Certificate", "EICR", "EPC", "Deposit Protection Certificate", "Tenancy Agreement", "Other"];
        const types = Object.keys(byType).sort((a, b) => {
            const ai = typeOrder.indexOf(a);
            const bi = typeOrder.indexOf(b);
            if (ai !== -1 && bi !== -1) return ai - bi;
            if (ai !== -1) return -1;
            if (bi !== -1) return 1;
            return (a || "").localeCompare(b || "");
        });

        if (types.length === 0) {
            container.innerHTML = `<div class="empty-state">No documents found for this property.</div>`;
            return;
        }

        container.innerHTML = types.map((type) => {
            const docs = (byType[type] || []).slice().sort((a, b) => {
                const aDate = a.scanned_at || a.imported_at || a.batch_date || "";
                const bDate = b.scanned_at || b.imported_at || b.batch_date || "";
                return (bDate || "").localeCompare(aDate || "");
            });
            const sectionSlug = docTypeToSectionSlug(type);
            const sectionId = "property-doc-group-" + sectionSlug;

            let groupBody = "";
            if (docs.length === 0) {
                groupBody = `
                    <div class="property-doc-empty">
                        <span class="property-doc-empty-text">No ${(type || "").replace(/</g, "&lt;")} uploaded yet</span>
                    </div>
                `;
            } else {
                groupBody = docs.map((doc) => {
                    const date = formatDate(doc.scanned_at || doc.imported_at || doc.batch_date);
                    const keySummary = (doc.key_fields_summary || "").trim();
                    const keyHtml = keySummary ? `<div class="doc-item-summary">${(keySummary || "").replace(/</g, "&lt;")}</div>` : "";
                    let complianceHtml = "";
                    if (doc.compliance_status && doc.compliance_status !== "no_expiry") {
                        const cls = (doc.compliance_status || "").replace("_", "-");
                        let badgeText = doc.compliance_status === "expired" ? "Expired" : doc.compliance_status === "expiring_soon" ? "Expiring" : "Valid";
                        if (doc.expiry_date) badgeText += " · " + formatDate(doc.expiry_date);
                        complianceHtml = `<span class="doc-item-compliance-badge compliance-badge-${cls}">${badgeText}</span>`;
                    }
                    let urgencyClass = doc.compliance_status === "expired" ? " doc-card-expired" : doc.compliance_status === "expiring_soon" ? " doc-card-expiring" : "";
                    return `
                        <button type="button" class="doc-item${urgencyClass}" data-doc-id="${(doc.source_doc_id || "").replace(/"/g, "&quot;")}">
                            <div class="doc-item-main">
                                <div class="doc-item-title">
                                    <span class="doc-item-icon">${docIcon(doc.doc_type)}</span>
                                    <span>${(doc.doc_name || doc.doc_type || doc.source_doc_id || "Document").replace(/</g, "&lt;")}</span>
                                </div>
                                <div class="doc-item-meta">
                                    <span class="doc-item-meta-text">${date}</span>
                                    ${keyHtml}
                                </div>
                            </div>
                            <div class="doc-item-badges">
                                <span class="status-badge ${statusClass(doc.status)}"><span class="dot"></span>${statusLabel(doc.status)}</span>
                                ${complianceHtml}
                            </div>
                        </button>
                    `;
                }).join("");
            }

            return `
                <section class="property-doc-group" id="${sectionId}">
                    <div class="property-doc-group-header">
                        <h2 class="property-doc-group-title">${(type || "").replace(/</g, "&lt;")}</h2>
                        <span class="property-doc-group-count">${docs.length} document${docs.length === 1 ? "" : "s"}</span>
                    </div>
                    <div class="property-doc-group-body">
                        ${groupBody}
                    </div>
                </section>
            `;
        }).join("");

        container.querySelectorAll(".doc-item").forEach((el) => {
            el.addEventListener("click", () => {
                const docId = el.getAttribute("data-doc-id");
                if (docId) selectDocument(docId);
            });
        });
    }

    // ── Property detail view: document drawer ────────────────────────────────
    async function selectDocument(sourceDocId) {
        selectedDocId = sourceDocId;

        // Highlight selected doc (property page cards)
        $$(".doc-item").forEach((el) => {
            el.classList.toggle("selected", el.getAttribute("data-doc-id") === sourceDocId);
        });
        const wrapper = $("#detail-drawer-wrapper");
        const drawer = $("#detail-drawer");
        if (wrapper) wrapper.classList.remove("hidden");
        if (drawer) drawer.classList.remove("hidden");
        if (!drawer) return;

        // Try to find from in-memory documents first
        const localDoc = (propertyDocuments || []).find(d => d.source_doc_id === sourceDocId);
        if (localDoc) {
            renderDrawer(localDoc);
        }

        // Fetch full detail (with fields) from API to ensure consistency
        const fullDoc = await fetchDocumentDetail(sourceDocId);
        if (fullDoc && fullDoc.source_doc_id === selectedDocId) {
            renderDrawer(fullDoc);
        }
    }

    function renderDrawer(doc) {
        if ($(".drawer-split-left")) {
            renderDrawerSplit(doc);
        }
    }

    function initDocumentViewerPage() {
        const closeBtn = $("#document-view-close");
        const verifyBtn = $("#document-view-verify");
        const issueToggleBtn = $("#document-issue-toggle");
        const issueForm = $("#document-issue-form");
        const issueCancelBtn = $("#document-issue-cancel");
        const issueSubmitBtn = $("#document-issue-submit");
        const issueFeedbackEl = $("#document-issue-feedback");
        const issueHelperEl = $("#document-issue-helper");
        const issueLatestEl = $("#document-issue-latest");
        const issueThreadEl = $("#document-issue-thread");
        const issueThreadBodyEl = $("#document-issue-thread-body");
        const issueThreadMetaEl = $("#document-issue-thread-meta");
        const issueMessageForm = $("#document-issue-message-form");
        const issueMessageInput = $("#document-issue-message-input");
        const issueDeliveryPillEl = $("#document-issue-delivery-pill");
        if (closeBtn) {
            const goArchive = () => {
                const url =
                    (window.MORPHIQ_PORTAL && window.MORPHIQ_PORTAL.archiveUrl) ||
                    `${withClientQuery("/properties")}#properties`;
                window.location.href = url;
            };
            closeBtn.addEventListener("click", goArchive);
            document.addEventListener("keydown", function documentViewEscape(ev) {
                if (ev.key === "Escape") {
                    ev.preventDefault();
                    goArchive();
                }
            });
        }

        const cfg = window.MORPHIQ_DOCUMENT_VIEW || {};
        const sourceDocId = cfg.sourceDocId;
        const docIdRaw = cfg.docId;
        const docIdNum = docIdRaw != null && docIdRaw !== "" ? Number(docIdRaw) : NaN;
        const useDocId = Number.isFinite(docIdNum) && docIdNum > 0;
        const canReportIssue = !!cfg.canReportIssue;
        const fieldsEl = $("#document-view-summary-fields");
        const pdfInner = $("#document-view-pdf-inner");
        const titleEl = $("#document-view-title");
        const addressEl = $("#document-view-address");
        const statusEl = $("#document-view-status");
        if (!fieldsEl || !pdfInner) return;
        if (!sourceDocId && !useDocId) return;

        const esc = (s) => String(s ?? "").replace(/</g, "&lt;");
        const formatDateTime = (value) => {
            if (!value) return "—";
            const d = new Date(value);
            if (Number.isNaN(d.getTime())) return esc(String(value));
            return esc(
                d.toLocaleString("en-GB", {
                    day: "2-digit",
                    month: "short",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                })
            );
        };
        const reasonLabel = (reasonCode) =>
            ({
                image_quality: "Image quality",
                incorrect_field: "Incorrect field",
                wrong_document_type: "Wrong document type",
                missing_pages: "Missing pages",
                duplicate_document: "Duplicate document",
                other: "Other",
            }[String(reasonCode || "").trim()] || statusLabel(String(reasonCode || "").trim()));
        const queueLabel = (queue) =>
            ({
                review_queue: "Review queue",
                rescan_queue: "Re-scan queue",
            }[String(queue || "").trim()] || "Unassigned");
        let currentDoc = null;
        let latestIssueId = null;

        function setIssueFeedback(message, tone) {
            if (!issueFeedbackEl) return;
            if (!message) {
                issueFeedbackEl.hidden = true;
                issueFeedbackEl.textContent = "";
                issueFeedbackEl.className = "document-issue-feedback";
                return;
            }
            issueFeedbackEl.hidden = false;
            issueFeedbackEl.textContent = message;
            issueFeedbackEl.className = `document-issue-feedback document-issue-feedback--${tone || "info"}`;
        }

        function setDeliveryStatus(deliveryStatus) {
            if (!issueDeliveryPillEl) return;
            issueDeliveryPillEl.className = `status-badge ${statusClass(deliveryStatus)}`;
            issueDeliveryPillEl.innerHTML = `<span class="dot"></span>${statusLabel(deliveryStatus)}`;
        }

        function renderIssueSummary(doc) {
            const issueSummary = doc.issue_summary || {};
            latestIssueId = issueSummary.latest_issue_id || null;
            setDeliveryStatus(doc.current_delivery_status || "verified");
            if (issueHelperEl) {
                issueHelperEl.textContent =
                    doc.current_delivery_status === "reported_under_review"
                        ? "This document is visible to the client, but it is currently back in MorphIQ's exception workflow until the fix is re-verified."
                        : "Verified documents stay visible here. If something looks wrong, you can send it back into the MorphIQ rework flow.";
            }
            if (issueLatestEl) {
                if (!latestIssueId) {
                    issueLatestEl.innerHTML =
                        '<div class="document-issue-empty">No open or prior rework tickets for this document.</div>';
                } else {
                    issueLatestEl.innerHTML = `
                        <div class="document-issue-summary-card">
                            <div>
                                <div class="document-issue-summary-label">Latest ticket</div>
                                <div class="document-issue-summary-title">Issue #${esc(latestIssueId)}</div>
                            </div>
                            <div class="document-issue-summary-meta">
                                <span class="status-badge ${statusClass(issueSummary.open_status || issueSummary.latest_status || "new")}"><span class="dot"></span>${statusLabel(issueSummary.open_status || issueSummary.latest_status || "new")}</span>
                                <span>${esc(reasonLabel(issueSummary.reason_code))}</span>
                                <span>${esc(queueLabel(issueSummary.target_queue))}</span>
                            </div>
                        </div>
                    `;
                }
            }
            if (issueToggleBtn) {
                issueToggleBtn.hidden = !canReportIssue;
                issueToggleBtn.textContent =
                    doc.current_delivery_status === "reported_under_review"
                        ? "Update reported issue"
                        : "Report a problem";
            }
        }

        function renderIssueDetail(detail) {
            const issue = (detail && detail.issue) || null;
            const messages = (detail && detail.messages) || [];
            const versions = (detail && detail.versions) || [];
            if (!issue || !issueThreadEl || !issueThreadBodyEl) {
                if (issueThreadEl) issueThreadEl.hidden = true;
                if (issueMessageForm) issueMessageForm.hidden = true;
                return;
            }
            latestIssueId = issue.id;
            issueThreadEl.hidden = false;
            if (issueThreadMetaEl) {
                issueThreadMetaEl.textContent = `${reasonLabel(issue.reason_code)} · ${queueLabel(issue.target_queue)} · ${statusLabel(issue.status)}`;
            }
            const versionItems = versions
                .map((version) => {
                    const label =
                        version.kind === "reported_snapshot"
                            ? "Original delivered version captured"
                            : "Corrected version captured after re-verification";
                    return `<div class="document-issue-timeline-item">
                        <div class="document-issue-timeline-dot"></div>
                        <div>
                            <div class="document-issue-timeline-title">${label}</div>
                            <div class="document-issue-timeline-meta">${formatDateTime(version.created_at)}</div>
                        </div>
                    </div>`;
                })
                .join("");
            const messageItems = messages
                .map((message) => {
                    const author = message.author_name || (message.author_role === "admin" ? "MorphIQ" : "Client");
                    const linkedDoc = message.linked_document_id ? ` · Doc ${esc(message.linked_document_id)}` : "";
                    return `<div class="document-issue-message ${message.author_role === "admin" ? "document-issue-message--staff" : ""}">
                        <div class="document-issue-message-head">
                            <strong>${esc(author)}</strong>
                            <span>${formatDateTime(message.created_at)}${linkedDoc}</span>
                        </div>
                        <div class="document-issue-message-body">${esc(message.body)}</div>
                    </div>`;
                })
                .join("");
            issueThreadBodyEl.innerHTML = `
                <div class="document-issue-thread-topline">
                    <div class="document-issue-thread-status">
                        <span class="status-badge ${statusClass(issue.status)}"><span class="dot"></span>${statusLabel(issue.status)}</span>
                        <span>Priority ${esc(issue.priority || "normal")}</span>
                        <span>${esc(issue.assigned_user_name || "Unassigned")}</span>
                    </div>
                    <div class="document-issue-thread-note">${esc(issue.note || "No extra note was added to this report.")}</div>
                </div>
                <div class="document-issue-timeline">${versionItems || '<div class="document-issue-empty">No audit snapshots yet.</div>'}</div>
                <div class="document-issue-message-list">${messageItems || '<div class="document-issue-empty">No support messages yet.</div>'}</div>
            `;
            if (issueMessageForm) {
                issueMessageForm.hidden = !canReportIssue;
            }
        }

        async function loadIssueDetail(issueId) {
            if (!issueId) {
                renderIssueDetail(null);
                return null;
            }
            try {
                const response = await fetch(withClientQuery(`/api/issues/${encodeURIComponent(issueId)}`), {
                    credentials: "same-origin",
                });
                if (!response.ok) throw new Error(String(response.status));
                const detail = await response.json();
                renderIssueDetail(detail);
                return detail;
            } catch (error) {
                if (issueThreadEl) issueThreadEl.hidden = true;
                return null;
            }
        }

        const detailUrl = useDocId
            ? `/api/documents/by-id/${encodeURIComponent(docIdNum)}`
            : `/api/documents/${encodeURIComponent(sourceDocId)}`;

        fetch(withClientQuery(detailUrl), { credentials: "same-origin" })
            .then((r) => {
                if (!r.ok) throw new Error(String(r.status));
                return r.json();
            })
            .then((doc) => {
                currentDoc = doc;
                if (titleEl) titleEl.textContent = doc.doc_type || doc.doc_name || "Document";
                if (addressEl) addressEl.textContent = doc.property_address || "";
                if (statusEl) {
                    const delivery = doc.current_delivery_status || "verified";
                    const deliveryBadge =
                        delivery !== "verified"
                            ? `<span class="status-badge ${statusClass(delivery)}"><span class="dot"></span>${statusLabel(delivery)}</span>`
                            : "";
                    statusEl.innerHTML = `<div class="document-view-status-stack"><span class="status-badge ${statusClass(doc.status)}"><span class="dot"></span>${statusLabel(doc.status)}</span>${deliveryBadge}</div>`;
                }
                renderIssueSummary(doc);
                loadIssueDetail(doc.issue_summary && doc.issue_summary.latest_issue_id);
                if (verifyBtn) {
                    const needsReview = ["new", "ai_prefilled", "needs_review"].includes(
                        String(doc.status || "").toLowerCase()
                    );
                    verifyBtn.hidden = !needsReview;
                    verifyBtn.disabled = false;
                    verifyBtn.textContent = "Mark Verified";
                    verifyBtn.onclick = async () => {
                        verifyBtn.disabled = true;
                        verifyBtn.textContent = "Verifying...";
                        try {
                            const response = await fetch(
                                withClientQuery(
                                    `/api/documents/by-id/${encodeURIComponent(doc.id)}/verify`
                                ),
                                { method: "POST", credentials: "same-origin" }
                            );
                            const payload = await response.json().catch(() => ({}));
                            if (!response.ok || !payload.success) {
                                throw new Error(payload.error || "Verification failed");
                            }
                            window.location.reload();
                        } catch (error) {
                            verifyBtn.disabled = false;
                            verifyBtn.textContent = "Mark Verified";
                            window.alert(error && error.message ? error.message : "Verification failed");
                        }
                    };
                }

                const fields = doc.fields || {};
                const fieldKeys = Object.keys(fields);
                let html = "";
                const coreFields = [
                    ["Document ID", doc.source_doc_id],
                    ["Document Name", doc.doc_name],
                    ["Client", doc.client_name],
                    ["Property", doc.property_address],
                    ["Scanned", formatDate(doc.scanned_at || doc.imported_at)],
                    ["Batch Date", doc.batch_date || "—"],
                ];
                coreFields.forEach(([label, value]) => {
                    if (value && value !== "—") {
                        html += `<div class="field-item"><div class="field-item-label">${esc(label)}</div><div class="field-item-value">${esc(value)}</div></div>`;
                    }
                });
                if (fieldKeys.length > 0) {
                    html += `<div class="field-item" style="margin-top: 10px; padding-top: 14px; border-top: 1px solid var(--border);"><div class="field-item-label" style="color: var(--accent); font-size: 10px;">Verified Fields</div></div>`;
                    fieldKeys.forEach((key) => {
                        const f = fields[key];
                        html += `<div class="field-item"><div class="field-item-label">${esc(f.label || fieldLabel(key))}</div><div class="field-item-value">${esc(f.value || "—")}</div></div>`;
                    });
                } else {
                    html += `<div class="no-fields"><div class="no-fields-icon">📋</div>No verified fields extracted yet.</div>`;
                }
                if (doc.reviewed_by) {
                    html += `<div class="field-item" style="margin-top:14px;"><div class="field-item-label">Verification</div><div class="review-info">Verified by <strong>${esc(doc.reviewed_by)}</strong><br>${esc(formatDate(doc.reviewed_at))}</div></div>`;
                }
                fieldsEl.innerHTML = html;

                const pdfProxyUrl = doc.id
                    ? withClientQuery(`/api/documents/by-id/${encodeURIComponent(doc.id)}/pdf`)
                    : withClientQuery(
                          `/api/documents/by-source/${encodeURIComponent(doc.source_doc_id || "")}/pdf`
                      );
                const scanstationPlain =
                    (doc.pdf_url && String(doc.pdf_url).split("#")[0]) || pdfProxyUrl;
                const pdfViewerHash = "#toolbar=0&navpanes=0&page=1&zoom=page-width";
                const pdfUrlWithZoom = doc.pdf_url
                    ? `${String(doc.pdf_url).split("#")[0]}${pdfViewerHash}`
                    : `${scanstationPlain}${pdfViewerHash}`;
                const hasPdf = !!(doc.pdf_path || doc.pdf_url || (doc.client_name && doc.source_doc_id));

                if (hasPdf) {
                    if (window.MorphIQPortalPdf && typeof pdfjsLib !== "undefined") {
                        MorphIQPortalPdf.mount(pdfInner, pdfProxyUrl);
                    } else {
                        pdfInner.innerHTML = `<iframe class="document-view-pdf-iframe" src="${scanstationPlain}${pdfViewerHash}" title="PDF Preview"></iframe>`;
                    }
                } else {
                    pdfInner.innerHTML = `<div class="document-view-pdf-missing"><span>PDF not available</span><span class="document-view-pdf-missing-id">${esc(doc.source_doc_id)}</span></div>`;
                }

                const openBtn = $("#document-view-open-pdf");
                const dlBtn = $("#document-view-download");
                if (openBtn) {
                    openBtn.disabled = !hasPdf;
                    openBtn.style.opacity = hasPdf ? "1" : "0.4";
                    openBtn.onclick = () => {
                        if (hasPdf) {
                            const openUrl =
                                window.MorphIQPortalPdf && typeof pdfjsLib !== "undefined"
                                    ? pdfProxyUrl + pdfViewerHash
                                    : pdfUrlWithZoom;
                            window.open(openUrl, "_blank");
                        }
                    };
                }
                if (dlBtn) {
                    dlBtn.disabled = !hasPdf;
                    dlBtn.style.opacity = hasPdf ? "1" : "0.4";
                    dlBtn.onclick = () => {
                        if (!hasPdf) return;
                        const a = document.createElement("a");
                        a.href =
                            window.MorphIQPortalPdf && typeof pdfjsLib !== "undefined"
                                ? pdfProxyUrl
                                : scanstationPlain;
                        a.download = `${doc.source_doc_id || "document"}.pdf`;
                        a.click();
                    };
                }
            })
            .catch(() => {
                fieldsEl.innerHTML = `<div class="empty-state">Could not load this document.</div>`;
                pdfInner.innerHTML = `<div class="document-view-pdf-missing">Document not found or access denied.</div>`;
            });

        if (issueToggleBtn && issueForm) {
            issueToggleBtn.addEventListener("click", () => {
                issueForm.hidden = !issueForm.hidden;
                if (!issueForm.hidden) {
                    setIssueFeedback("", "info");
                    const reasonEl = $("#document-issue-reason");
                    if (reasonEl) reasonEl.focus();
                }
            });
        }
        if (issueCancelBtn && issueForm) {
            issueCancelBtn.addEventListener("click", () => {
                issueForm.hidden = true;
                setIssueFeedback("", "info");
            });
        }
        if (issueForm) {
            issueForm.addEventListener("submit", async (event) => {
                event.preventDefault();
                if (!currentDoc || !currentDoc.id) return;
                const reasonEl = $("#document-issue-reason");
                const noteEl = $("#document-issue-note");
                const attachmentEl = $("#document-issue-attachment");
                const openSupportEl = $("#document-issue-open-support");
                const formData = new FormData();
                formData.set("reason_code", reasonEl ? reasonEl.value : "other");
                formData.set("note", noteEl ? noteEl.value : "");
                if (openSupportEl && openSupportEl.checked) formData.set("open_support", "1");
                if (attachmentEl && attachmentEl.files && attachmentEl.files[0]) {
                    formData.set("attachment", attachmentEl.files[0]);
                }
                if (issueSubmitBtn) {
                    issueSubmitBtn.disabled = true;
                    issueSubmitBtn.textContent = "Sending...";
                }
                try {
                    const response = await fetch(
                        withClientQuery(`/api/documents/by-id/${encodeURIComponent(currentDoc.id)}/issues`),
                        {
                            method: "POST",
                            credentials: "same-origin",
                            body: formData,
                        }
                    );
                    const payload = await response.json().catch(() => ({}));
                    if (!response.ok || !payload.issue) {
                        throw new Error(payload.error || "Could not report this document");
                    }
                    currentDoc.current_delivery_status = "reported_under_review";
                    currentDoc.issue_summary = currentDoc.issue_summary || {};
                    currentDoc.issue_summary.latest_issue_id = payload.issue.id;
                    currentDoc.issue_summary.open_issue_id = payload.issue.id;
                    currentDoc.issue_summary.open_status = payload.issue.status;
                    currentDoc.issue_summary.latest_status = payload.issue.status;
                    currentDoc.issue_summary.reason_code = payload.issue.reason_code;
                    currentDoc.issue_summary.target_queue = payload.issue.target_queue;
                    renderIssueSummary(currentDoc);
                    await loadIssueDetail(payload.issue.id);
                    issueForm.reset();
                    issueForm.hidden = true;
                    setIssueFeedback(
                        payload.created === false
                            ? "This document already had an open issue, so your update was attached to the existing ticket."
                            : "Your report has been sent to MorphIQ and the document is now marked under review.",
                        "success"
                    );
                } catch (error) {
                    setIssueFeedback(
                        error && error.message ? error.message : "Could not report this document.",
                        "error"
                    );
                } finally {
                    if (issueSubmitBtn) {
                        issueSubmitBtn.disabled = false;
                        issueSubmitBtn.textContent = "Send to MorphIQ";
                    }
                }
            });
        }
        if (issueMessageForm && issueMessageInput) {
            issueMessageForm.addEventListener("submit", async (event) => {
                event.preventDefault();
                if (!latestIssueId) return;
                const body = String(issueMessageInput.value || "").trim();
                if (!body) return;
                const sendBtn = $("#document-issue-message-send");
                if (sendBtn) sendBtn.disabled = true;
                try {
                    const response = await fetch(
                        withClientQuery(`/api/issues/${encodeURIComponent(latestIssueId)}/messages`),
                        {
                            method: "POST",
                            credentials: "same-origin",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ body }),
                        }
                    );
                    const payload = await response.json().catch(() => ({}));
                    if (!response.ok || !payload.message) {
                        throw new Error(payload.error || "Could not send update");
                    }
                    issueMessageInput.value = "";
                    await loadIssueDetail(latestIssueId);
                } catch (error) {
                    window.alert(error && error.message ? error.message : "Could not send update");
                } finally {
                    if (sendBtn) sendBtn.disabled = false;
                }
            });
        }
    }

    function renderDrawerSplit(doc) {
        const pdfContainer = $("#drawer-pdf-container");
        const pdfPlaceholder = $("#drawer-pdf-placeholder");
        const docIconEl = $("#drawer-doc-icon");
        const docNameEl = $("#drawer-doc-name");
        const docIdEl = $("#drawer-doc-id");
        const docStatusEl = $("#drawer-doc-status");
        const coreInfoEl = $("#drawer-core-info");
        const verifiedFieldsEl = $("#drawer-verified-fields");
        const downloadBtn = $("#drawer-download-pdf");
        const fullscreenBtn = $("#drawer-fullscreen");

        const pdfProxyUrl = doc.id
            ? withClientQuery(`/api/documents/by-id/${encodeURIComponent(doc.id)}/pdf`)
            : withClientQuery(`/api/documents/by-source/${encodeURIComponent(doc.source_doc_id || "")}/pdf`);
        /* Use pdf_url from API when present, else fall back to the portal's same-origin PDF proxy. */
        const pdfUrlPlain = (doc.pdf_url && doc.pdf_url.split("#")[0]) || pdfProxyUrl;
        const pdfViewerHash = "#toolbar=0&navpanes=0&page=1&zoom=page-width";
        const pdfUrlWithZoom = doc.pdf_url
            ? `${doc.pdf_url.split("#")[0]}${pdfViewerHash}`
            : `${pdfUrlPlain}${pdfViewerHash}`;
        const hasPdf = !!(doc.pdf_path || doc.pdf_url || (doc.client_name && doc.source_doc_id));

        if (docIconEl) docIconEl.textContent = docIcon(doc.doc_type || "");
        if (docNameEl) docNameEl.textContent = doc.doc_type || doc.doc_name || "Document";
        if (docIdEl) docIdEl.textContent = doc.source_doc_id || "—";
        if (docStatusEl) {
            docStatusEl.innerHTML = `<span class="status-badge ${statusClass(doc.status)}"><span class="dot"></span>${statusLabel(doc.status)}</span>`;
        }

        if (pdfContainer) {
            if (hasPdf) {
                pdfContainer.innerHTML = `<iframe src="${pdfUrlPlain}${pdfViewerHash}" title="PDF Preview"></iframe>`;
            } else {
                pdfContainer.innerHTML = `
                    <div class="drawer-pdf-placeholder">
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

        if (coreInfoEl) {
            coreInfoEl.innerHTML = [
                ["Client", doc.client_name || "—"],
                ["Property", doc.property_address || "—"],
                ["Scanned", formatDate(doc.scanned_at || doc.imported_at)],
                ["Batch", doc.batch_date || "—"],
            ]
                .map(([label, value]) => `<div class="drawer-field-item"><span class="drawer-field-label">${label}</span><span class="drawer-field-value">${value}</span></div>`)
                .join("");
        }

        const fields = doc.fields || {};
        const fieldKeys = Object.keys(fields);
        if (verifiedFieldsEl) {
            if (fieldKeys.length === 0) {
                verifiedFieldsEl.innerHTML = `<div class="drawer-no-fields">No verified fields extracted yet.</div>`;
            } else {
                verifiedFieldsEl.innerHTML = fieldKeys
                    .map((key) => {
                        const f = fields[key];
                        const label = (f && f.label) || fieldLabel(key);
                        const value = (f && f.value) || "—";
                        return `<div class="drawer-field-item"><span class="drawer-field-label">${label}</span><span class="drawer-field-value">${value}</span></div>`;
                    })
                    .join("");
            }
        }

        if (downloadBtn) {
            if (hasPdf) {
                downloadBtn.href = pdfUrlPlain;
                downloadBtn.target = "_blank";
                downloadBtn.rel = "noopener";
                downloadBtn.style.pointerEvents = "";
                downloadBtn.style.opacity = "1";
            } else {
                downloadBtn.removeAttribute("href");
                downloadBtn.style.pointerEvents = "none";
                downloadBtn.style.opacity = "0.5";
            }
        }
        if (fullscreenBtn) {
            if (hasPdf) {
                fullscreenBtn.href = pdfUrlWithZoom;
                fullscreenBtn.target = "_blank";
                fullscreenBtn.rel = "noopener";
                fullscreenBtn.style.pointerEvents = "";
                fullscreenBtn.style.opacity = "1";
            } else {
                fullscreenBtn.removeAttribute("href");
                fullscreenBtn.style.pointerEvents = "none";
                fullscreenBtn.style.opacity = "0.5";
            }
        }
        const closeBtnDrawer = $("#drawer-close-btn");
        if (closeBtnDrawer) closeBtnDrawer.onclick = closeDrawer;
    }

    // ── Init ────────────────────────────────────────────────────────────────
    async function initDashboardOverview(uploadModalApi) {
        const overviewRoot = $("#dashboard-overview");
        if (!overviewRoot) return;

        const cfg = window.MORPHIQ_PORTAL || {};
        const clientName = cfg.clientName || (new URLSearchParams(window.location.search).get("client") || "");

        function dashRelativeTime(ts) {
            if (!ts) return "";
            const d = new Date(ts);
            if (Number.isNaN(d.getTime())) return ts;
            const diffMs = Date.now() - d.getTime();
            const diffM = Math.floor(diffMs / 60000);
            const diffH = Math.floor(diffMs / 3600000);
            const diffD = Math.floor(diffMs / 86400000);
            if (diffM < 1) return "Just now";
            if (diffM < 60) return `${diffM} min ago`;
            if (diffH < 24) return `${diffH} h ago`;
            if (diffD === 1) return "Yesterday";
            if (diffD < 7) return `${diffD} days ago`;
            return d.toLocaleDateString();
        }

        function ringTierClass(pct) {
            if (pct < 30) return "dashboard-ring-fg--low";
            if (pct <= 70) return "dashboard-ring-fg--mid";
            return "dashboard-ring-fg--high";
        }

        function barTierClass(pct) {
            if (pct < 20) return "dashboard-coverage-fill--red";
            if (pct <= 60) return "dashboard-coverage-fill--amber";
            return "dashboard-coverage-fill--green";
        }

        const pillEl = $("#dash-client-pill");
        if (pillEl) {
            const nm = (clientName || "").trim();
            pillEl.textContent = nm || "—";
        }

        try {
            const dashRes = await fetch("/api/dashboard-stats", { credentials: "same-origin" });
            const dash = await dashRes.json().catch(() => ({}));
            if (dash.error) {
                console.error("Dashboard stats error:", dash.error, dash.details);
            }

            const totalProps = dash.total_properties ?? 0;
            const totalDocs = dash.total_documents ?? 0;
            const overdue = dash.overdue_actions ?? 0;
            const scorePct = Math.round(dash.compliance_score_pct ?? 0);
            const reqPresent = dash.required_present ?? 0;
            const reqTotal = dash.required_total ?? 0;
            const categoryCoverage = dash.category_coverage || [];
            const needsAttention = dash.needs_attention || [];
            const recentActivity = dash.recent_activity || [];

            const statPropsEl = $("#dash-stat-properties");
            const statDocsEl = $("#dash-stat-documents");
            const statOverdueEl = $("#dash-stat-overdue");

            if (statPropsEl) {
                const val = statPropsEl.querySelector(".dashboard-stat-value");
                if (val) val.textContent = totalProps;
            }
            if (statDocsEl) {
                const val = statDocsEl.querySelector(".dashboard-stat-value");
                if (val) val.textContent = totalDocs;
            }
            if (statOverdueEl) {
                const val = statOverdueEl.querySelector(".dashboard-stat-value");
                const sub = statOverdueEl.querySelector(".dashboard-stat-sub");
                if (val) val.textContent = overdue;
                if (sub) sub.textContent = overdue > 0 ? "Expired certificates" : "All clear";
                statOverdueEl.classList.toggle("is-clear", overdue === 0);
            }

            const ringArc = $("#dash-compliance-ring-arc");
            const ringPct = $("#dash-compliance-pct");
            const ringCap = $("#dash-compliance-ring-caption");
            const R = 88;
            const C = 2 * Math.PI * R;
            if (ringArc) {
                ringArc.style.strokeDasharray = `${(scorePct / 100) * C} ${C}`;
                ringArc.classList.remove("dashboard-ring-fg--low", "dashboard-ring-fg--mid", "dashboard-ring-fg--high");
                ringArc.classList.add(ringTierClass(scorePct));
            }
            if (ringPct) ringPct.textContent = String(scorePct);
            if (ringCap) {
                ringCap.textContent =
                    reqTotal > 0
                        ? `${reqPresent} of ${reqTotal} required documents present`
                        : "No properties yet";
            }

            const coverageRoot = $("#dash-coverage-bars");
            if (coverageRoot) {
                if (!categoryCoverage.length) {
                    coverageRoot.innerHTML = `<div class="dashboard-empty">No coverage data yet.</div>`;
                } else {
                    coverageRoot.innerHTML = categoryCoverage
                        .map((h) => {
                            const total = h.total || 0;
                            const present = h.present || 0;
                            const pct = total > 0 ? Math.round((present / total) * 100) : 0;
                            const tier = barTierClass(pct);
                            const safeLabel = String(h.label || "").replace(/</g, "&lt;");
                            return `
                                <div class="dashboard-coverage-row">
                                    <div class="dashboard-coverage-label">${safeLabel} — ${present} / ${total} properties</div>
                                    <div class="dashboard-coverage-track" role="img" aria-label="${present} of ${total} properties">
                                        <div class="dashboard-coverage-fill ${tier}" style="width:${pct}%;"></div>
                                    </div>
                                    <div class="dashboard-coverage-count">${pct}%</div>
                                </div>
                            `;
                        })
                        .join("");
                }
            }

            const attentionRoot = $("#dash-needs-attention");
            if (attentionRoot) {
                if (!needsAttention.length) {
                    attentionRoot.innerHTML = `<div class="dashboard-empty">All clear — no overdue or expiring certificates.</div>`;
                } else {
                    attentionRoot.innerHTML = needsAttention
                        .map((g) => {
                            const dot =
                                g.dot === "amber" ? "dash-attn-dot--amber" : "dash-attn-dot--red";
                            const title = String(g.title || "").replace(/</g, "&lt;");
                            const href = escapeAttr(g.href || "#");
                            return `
                            <div class="dashboard-attention-item dashboard-attention-item--grouped">
                                <span class="dash-attn-dot ${dot}" aria-hidden="true"></span>
                                <div class="dashboard-attention-item-body">
                                    <div class="dashboard-attention-title"><a href="${href}">${title}</a></div>
                                    <div class="dashboard-attention-meta">${String(g.label_str || "").replace(/</g, "&lt;")} — ${String(g.meta || "").replace(/</g, "&lt;")}</div>
                                </div>
                            </div>`;
                        })
                        .join("");
                }
                const viewAllLink = $("#dash-attention-view-all");
                if (viewAllLink) {
                    let href = "/compliance";
                    if (clientName) href += `?client=${encodeURIComponent(clientName)}`;
                    viewAllLink.href = href;
                }
            }

            const activityRoot = $("#dash-recent-activity");
            const activityViewAll = $("#dash-activity-view-all");
            if (activityViewAll) {
                let ahref = "/reports";
                if (clientName) ahref += `?client=${encodeURIComponent(clientName)}`;
                activityViewAll.href = ahref;
            }
            if (activityRoot) {
                if (!recentActivity.length) {
                    activityRoot.innerHTML = `<div class="dashboard-empty">No recent activity.</div>`;
                } else {
                    activityRoot.innerHTML = recentActivity
                        .map((e) => {
                            const dotClass =
                                e.kind === "resolved" ? "dash-act-dot--amber" : "dash-act-dot--green";
                            const addr = String(e.property_address || "").replace(/</g, "&lt;");
                            const line = String(e.description || "").replace(/</g, "&lt;");
                            const who = e.user_name ? ` · ${String(e.user_name).replace(/</g, "&lt;")}` : "";
                            return `
                            <div class="dashboard-activity-item">
                                <span class="dash-act-dot ${dotClass}" aria-hidden="true"></span>
                                <div class="dashboard-activity-body">
                                    <div class="dashboard-activity-text"><strong>${addr}</strong></div>
                                    <div class="dashboard-activity-text dashboard-activity-desc">${line}${who}</div>
                                    <div class="dashboard-activity-time">${dashRelativeTime(e.created_at)}</div>
                                </div>
                            </div>`;
                        })
                        .join("");
                }
            }

            const navUpload = $("#dash-nav-upload");
            if (navUpload && uploadModalApi) {
                navUpload.addEventListener("click", async () => {
                    try {
                        let url = "/api/properties";
                        if (clientName) url += `?client=${encodeURIComponent(clientName)}`;
                        const res = await fetch(url);
                        const data = await res.json().catch(() => ({}));
                        uploadModalApi.openUploadModal({ propertyList: (data && data.properties) || [] });
                    } catch (err) {
                        console.error("Failed to load properties for upload modal:", err);
                        uploadModalApi.openUploadModal({ propertyList: [] });
                    }
                });
            }
        } catch (err) {
            console.error("Failed to load dashboard overview data:", err);
        }
    }

    function escapeAttr(s) {
        if (s == null || s === undefined) return "";
        return String(s)
            .replace(/&/g, "&amp;")
            .replace(/"/g, "&quot;")
            .replace(/</g, "&lt;");
    }

    function initArchivePage() {
        // Search input
        const searchInput = $(".search-input");
        if (searchInput) {
            searchInput.addEventListener("input", (e) => {
                searchQuery = e.target.value;
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(() => applyFilters(), 150);
            });
        }

        // Left-panel property search
        const leftPanel = document.querySelector(".archive-panel-left");
        if (leftPanel) {
            // Ensure search input exists
            let searchEl = document.querySelector("#archive-property-search");
            if (!searchEl) {
                searchEl = document.createElement("input");
                searchEl.type = "text";
                searchEl.id = "archive-property-search";
                searchEl.className = "archive-property-search-input";
                searchEl.placeholder = "Search properties...";
                const heading = document.querySelector("#archive-properties-heading");
                if (heading) {
                    heading.insertAdjacentElement("afterend", searchEl);
                } else {
                    leftPanel.insertBefore(searchEl, leftPanel.firstChild);
                }
            }

            if (!searchEl.dataset.archiveSearchBound) {
                searchEl.addEventListener("input", (e) => {
                    listSearchQuery = e.target.value || "";
                    renderPropertyList();
                });
                searchEl.dataset.archiveSearchBound = "1";
            }

            // Ensure dropdown filter row exists
            const areaSelectExists = document.querySelector("#archive-area-filter-select");
            const postcodeSelectExists = document.querySelector("#archive-postcode-filter-select");
            if (!areaSelectExists || !postcodeSelectExists) {
                const row = document.createElement("div");
                row.className = "archive-property-filters-row";

                const areaSelect = document.createElement("select");
                areaSelect.id = "archive-area-filter-select";
                areaSelect.className = "archive-property-filter-select";
                areaSelect.setAttribute("aria-label", "Area");

                const postcodeSelect = document.createElement("select");
                postcodeSelect.id = "archive-postcode-filter-select";
                postcodeSelect.className = "archive-property-filter-select";
                postcodeSelect.setAttribute("aria-label", "Postcode");

                // Initial options (populated after fetchProperties)
                areaSelect.innerHTML = `<option value="">All areas</option>`;
                postcodeSelect.innerHTML = `<option value="">All postcodes</option>`;

                row.appendChild(areaSelect);
                row.appendChild(postcodeSelect);

                // Insert right after the search input (so search remains the first row)
                searchEl.insertAdjacentElement("afterend", row);

                // Bind change listeners
                areaSelect.addEventListener("change", (e) => {
                    archiveAreaFilter = e.target.value || "";
                    renderPropertyList();
                });
                postcodeSelect.addEventListener("change", (e) => {
                    archivePostcodePrefixFilter = e.target.value || "";
                    renderPropertyList();
                });
            }
        }

        document.querySelectorAll(".archive-workspace-mode-toggle .archive-workspace-mode-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                const mode = btn.getAttribute("data-workspace-mode") || "documents";
                setArchiveWorkspaceMode(mode);
            });
        });

        // Filter chips
        $$(".filter-chip").forEach(chip => {
            chip.addEventListener("click", () => {
                activeFilter = chip.getAttribute("data-filter");
                $$(".filter-chip").forEach(c => c.classList.toggle("active", c === chip));
                applyFilters();
            });
        });

        // Sort select (archive table: use id so we don't bind the status filter by mistake)
        const sortSelect = $("#archive-sort-select") || document.querySelector(".content-left .sort-select");
        if (sortSelect) {
            sortSelect.addEventListener("change", (e) => {
                currentSort = e.target.value;
                applyFilters();
            });
        }

        // Archive compliance status filter
        const statusFilter = $("#property-status-filter");
        if (statusFilter) {
            statusFilter.addEventListener("change", (e) => {
                archiveStatusFilter = e.target.value;
                applyFilters();
            });
        }

        // Stat card clicks: Total scrolls to table; others set compliance filter
        const resultsContainer = $(".results-container");
        const statTotal = $("#stat-total-props");
        const statCompliant = $("#stat-compliant");
        const statExpiring = $("#stat-expiring");
        const statNoncompliant = $("#stat-noncompliant");
        if (statTotal && resultsContainer) {
            statTotal.addEventListener("click", () => {
                resultsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
            });
        }
        function setStatusFilterAndApply(value) {
            archiveStatusFilter = value;
            if (statusFilter) statusFilter.value = value;
            applyFilters();
        }
        if (statCompliant) statCompliant.addEventListener("click", () => setStatusFilterAndApply("valid"));
        if (statExpiring) statExpiring.addEventListener("click", () => setStatusFilterAndApply("expiring_soon"));
        if (statNoncompliant) statNoncompliant.addEventListener("click", () => setStatusFilterAndApply("expired"));

        // Drawer close button
        const closeBtn = $(".drawer-close");
        if (closeBtn) {
            closeBtn.addEventListener("click", closeDrawer);
        }

        // Critical expiries: resolve/snooze delegation
        const criticalListEl = $("#archive-critical-list");
        if (criticalListEl) {
            criticalListEl.addEventListener("click", (e) => {
                const wrap = e.target.closest(".critical-expiry-card-compact");
                if (!wrap) return;
                if (e.target.closest("a.critical-expiry-view-btn")) return;
                const propertyId = wrap.getAttribute("data-property-id");
                const compType = wrap.getAttribute("data-comp-type");
                if (!propertyId || !compType) return;
                e.preventDefault();

                if (e.target.classList.contains("action-btn-resolve")) {
                    const form = wrap.querySelector(".action-resolve-form");
                    const opts = wrap.querySelector(".action-snooze-options");
                    if (form) form.style.display = "flex";
                    if (opts) opts.style.display = "none";
                    wrap.querySelector(".action-btn-resolve").style.display = "none";
                    wrap.querySelector(".action-btn-snooze").style.display = "none";
                    return;
                }
                if (e.target.classList.contains("action-cancel-btn")) {
                    const form = wrap.querySelector(".action-resolve-form");
                    if (form) { form.style.display = "none"; form.querySelector(".action-notes-input").value = ""; }
                    wrap.querySelector(".action-btn-resolve").style.display = "";
                    wrap.querySelector(".action-btn-snooze").style.display = "";
                    return;
                }
                if (e.target.classList.contains("action-confirm-btn")) {
                    const form = wrap.querySelector(".action-resolve-form");
                    const notes = form ? (form.querySelector(".action-notes-input").value || "").trim() : "";
                    wrap.classList.add("action-item-resolving");
                    fetch("/api/compliance/actions/resolve", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        credentials: "same-origin",
                        body: JSON.stringify({ property_id: parseInt(propertyId, 10), comp_type: compType, notes }),
                    })
                        .then((res) => res.ok ? fetchCriticalExpiries() : Promise.reject(new Error("Resolve failed")))
                        .catch((err) => {
                            console.error(err);
                            wrap.classList.remove("action-item-resolving");
                        });
                    return;
                }
                if (e.target.classList.contains("action-btn-snooze")) {
                    const opts = wrap.querySelector(".action-snooze-options");
                    const form = wrap.querySelector(".action-resolve-form");
                    if (opts) opts.style.display = opts.style.display === "none" ? "inline" : "none";
                    if (form) form.style.display = "none";
                    e.preventDefault();
                    return;
                }
                if (e.target.classList.contains("action-btn-snooze-days")) {
                    const days = parseInt(e.target.getAttribute("data-days"), 10);
                    if (!Number.isFinite(days)) return;
                    e.preventDefault();
                    fetch("/api/compliance/actions/snooze", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        credentials: "same-origin",
                        body: JSON.stringify({ property_id: parseInt(propertyId, 10), comp_type: compType, days }),
                    })
                        .then((res) => res.ok ? fetchCriticalExpiries() : Promise.reject(new Error("Snooze failed")))
                        .catch((err) => console.error(err));
                }
            });
        }

        // Export Report button (dashboard)
        const dashboardExportBtn = $("#dashboard-export-report");
        if (dashboardExportBtn) {
            dashboardExportBtn.addEventListener("click", () => {
                const client = (window.MORPHIQ_PORTAL && window.MORPHIQ_PORTAL.clientName) || (new URLSearchParams(window.location.search).get("client") || "");
                const url = "/api/compliance/report?format=pdf" + (client ? "&client=" + encodeURIComponent(client) : "");
                if (!client) {
                    alert("Please select a client first.");
                    return;
                }
                downloadReportPdf(url, dashboardExportBtn, "Export");
            });
        }

        // Load properties and critical expiries
        fetchProperties();
        fetchCriticalExpiries();
    }

    async function initPropertyPage(uploadModalApi) {
        const root = $("#property-detail-root");
        if (!root || !window.MORPHIQ_PROPERTY) {
            return;
        }

        currentPropertyId = window.MORPHIQ_PROPERTY.propertyId;

        // Drawer close button
        const closeBtn = $(".drawer-close");
        if (closeBtn) {
            closeBtn.addEventListener("click", closeDrawer);
        }

        // Drawer overlay: click outside to close
        const drawerOverlay = $("#drawer-overlay");
        if (drawerOverlay) {
            drawerOverlay.addEventListener("click", closeDrawer);
        }

        // Drawer tabs (archive page only; property page has no tabs)
        $$(".drawer-tab").forEach(tab => {
            tab.addEventListener("click", () => {
                switchDrawerTab(tab.getAttribute("data-tab"));
            });
        });

        // Export Report button (property pack PDF)
        const propertyExportBtn = $("#property-export-report");
        if (propertyExportBtn && currentPropertyId != null) {
            propertyExportBtn.addEventListener("click", () => {
                downloadReportPdf(
                    withClientQuery(`/api/properties/${currentPropertyId}/report?format=pdf`),
                    propertyExportBtn,
                    "Export Report"
                );
            });
        }

        // Download All Documents (ZIP pack)
        const downloadPackBtn = $("#property-download-pack");
        if (downloadPackBtn) {
            downloadPackBtn.addEventListener("click", async () => {
                const propertyId = currentPropertyId;
                if (propertyId == null) return;
                const originalText = downloadPackBtn.textContent;
                downloadPackBtn.textContent = "Preparing ZIP…";
                downloadPackBtn.disabled = true;
                try {
                    const res = await fetch(withClientQuery(`/api/properties/${propertyId}/download-pack`), {
                        method: "POST",
                        credentials: "same-origin",
                    });
                    if (!res.ok) {
                        const data = await res.json().catch(() => ({}));
                        const msg = (data && data.error) || `Download failed (${res.status})`;
                        alert(msg);
                        return;
                    }
                    const blob = await res.blob();
                    let filename = "Documents.zip";
                    const disp = res.headers.get("Content-Disposition");
                    if (disp) {
                        const match = disp.match(/filename\*?=(?:UTF-8'')?["']?([^"';]+)["']?/i) || disp.match(/filename=["']?([^"';]+)["']?/i);
                        if (match && match[1]) {
                            filename = match[1].trim();
                        }
                    }
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = filename;
                    a.click();
                    URL.revokeObjectURL(url);
                } finally {
                    downloadPackBtn.textContent = originalText;
                    downloadPackBtn.disabled = false;
                }
            });
        }

        // Upload Document: use shared modal with pre-selected property
        const uploadDocBtn = $("#property-upload-document");
        if (uploadDocBtn && uploadModalApi) {
            uploadDocBtn.addEventListener("click", () => {
                uploadModalApi.openUploadModal({ propertyId: currentPropertyId });
            });
        }

        // Escape: close drawer (upload modal Escape is handled in initUploadModal)
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && selectedDocId) {
                closeDrawer();
            }
        });

        // Search within this property's documents
        const searchInput = $(".search-input");
        if (searchInput) {
            searchInput.addEventListener("input", (e) => {
                const q = e.target.value.toLowerCase();
                const groups = $("#property-doc-groups");
                if (!groups || !propertyDocuments.length) return;

                if (!q) {
                    // Re-render original groups
                    renderPropertyDocuments(propertyDetail);
                    const countEl = $("#search-count");
                    if (countEl) {
                        countEl.style.display = "none";
                    }
                    return;
                }

                const filtered = propertyDocuments.filter((d) =>
                    (d.source_doc_id || "").toLowerCase().includes(q) ||
                    (d.doc_name || "").toLowerCase().includes(q) ||
                    (d.doc_type || "").toLowerCase().includes(q)
                );

                const byType = {};
                filtered.forEach((doc) => {
                    const key = doc.doc_type || "Other";
                    byType[key] = byType[key] || [];
                    byType[key].push(doc);
                });

                renderPropertyDocuments({
                    documents_by_type: byType,
                    documents: filtered,
                });

                const countEl = $("#search-count");
                if (countEl) {
                    countEl.textContent = `${filtered.length} result${filtered.length === 1 ? "" : "s"}`;
                    countEl.style.display = "block";
                }
            });
        }

        try {
            const detail = await fetchPropertyDetail(currentPropertyId);
            if (!detail) {
                const container = $("#property-doc-groups");
                if (container) {
                    container.innerHTML = `<div class="empty-state">Failed to load property details.</div>`;
                }
                return;
            }

            propertyDetail = detail;
            propertyDocuments = detail.documents || [];
            if (detail.client_name) chatClientName = detail.client_name;

            renderPropertyHeader(detail);
            renderComplianceSummary(detail);
            renderPropertyDocuments(detail);

            const focusType = window.MORPHIQ_PROPERTY && window.MORPHIQ_PROPERTY.focusType;
            if (focusType) {
                const card = document.querySelector(`.property-compliance-card[data-scroll-to*="${focusType.replace("_", "-")}"]`);
                if (card) card.classList.add("property-compliance-card-focus");
            }
        } catch (err) {
            console.error(err);
            const container = $("#property-doc-groups");
            if (container) {
                container.innerHTML = `<div class="empty-state">Failed to load property details.</div>`;
            }
        }
    }

    // ── Compliance dashboard: helpers ───────────────────────────────────────
    function dedupeComplianceActions(actions) {
        if (!actions || !actions.length) return [];
        const byKey = {};
        actions.forEach((a) => {
            const pid = a.property_id != null ? String(a.property_id) : "null";
            const type = (a.type || "").trim();
            const key = pid + "|" + type;
            const existing = byKey[key];
            if (!existing) {
                byKey[key] = a;
                return;
            }
            const existingExp = existing.expiry_date || "";
            const nextExp = a.expiry_date || "";
            if (nextExp > existingExp) {
                byKey[key] = a;
            }
        });
        return Object.values(byKey);
    }

    function setComplianceWorkspaceMode(mode) {
        const next = mode === "action" ? "action" : mode === "history" ? "history" : "health";
        complianceWorkspaceMode = next;
        const healthEl = document.getElementById("compliance-workspace-health");
        const actionEl = document.getElementById("compliance-workspace-action");
        const historyEl = document.getElementById("compliance-workspace-history");
        document.querySelectorAll(".compliance-workspace-mode-btn").forEach((btn) => {
            const on = btn.getAttribute("data-compliance-workspace") === next;
            btn.classList.toggle("active", on);
            btn.setAttribute("aria-selected", on ? "true" : "false");
        });
        if (healthEl) healthEl.hidden = next !== "health";
        if (actionEl) actionEl.hidden = next !== "action";
        if (historyEl) historyEl.hidden = next !== "history";
    }

    function complianceActionRowKey(propertyId, compType) {
        return `${propertyId != null ? propertyId : ""}:${(compType || "").trim()}`;
    }

    function sortComplianceActionsList(arr) {
        return [...arr].sort((a, b) => {
            const aSnoozed = !!a.snoozed;
            const bSnoozed = !!b.snoozed;
            if (aSnoozed !== bSnoozed) return aSnoozed ? 1 : -1;
            const orderA = a.sort_order ?? 2;
            const orderB = b.sort_order ?? 2;
            if (orderA !== orderB) return orderA - orderB;
            const daysA = a.sort_days ?? (orderA === 0 ? -9999 : orderA === 1 ? 0 : 9999);
            const daysB = b.sort_days ?? (orderB === 0 ? -9999 : orderB === 1 ? 0 : 9999);
            return orderA === 0 ? daysA - daysB : daysA - daysB;
        });
    }

    function filterComplianceActionsForList(actions) {
        const source = dedupeComplianceActions(actions || []);
        return source.filter((a) => {
            if (complianceTypeFilter !== "all" && (a.type || "").trim() !== complianceTypeFilter) return false;
            if (complianceSeverityFilter !== "all" && (a.status || "") !== complianceSeverityFilter) return false;
            return true;
        });
    }

    function buildComplianceActionCardHtml(a, clientName) {
        const status = a.status;
        const severityBarClass = status === "expired" ? "action-severity-bar expired" : status === "expiring_soon" ? "action-severity-bar expiring" : "action-severity-bar missing";

        let propertyHref = "#";
        if (a.property_id) {
            propertyHref = `/property/${a.property_id}`;
            if (clientName) propertyHref += `?client=${encodeURIComponent(clientName)}`;
        }

        const isSnoozed = !!a.snoozed;
        const snoozedUntil = (a.snoozed_until || "").slice(0, 10);
        const itemClass = isSnoozed ? "compliance-action-card snoozed" : "compliance-action-card";
        const pid = (a.property_id != null) ? String(a.property_id) : "";
        const ctype = (a.type || "").replace(/"/g, "&quot;");
        const typeLabel = (a.type_label || a.type || "").replace(/</g, "&lt;");
        const propertyText = (a.property || "Unknown property").replace(/</g, "&lt;");
        const displayText = (a.display_text || "").replace(/</g, "&lt;");

        const liabilityLine = status === "expired"
            ? `<div class="compliance-action-liability">Landlord liable for £6,000 fine · Property cannot be legally let</div>`
            : "";
        const snoozedLine = isSnoozed && snoozedUntil
            ? `<div class="compliance-action-snoozed-until">Snoozed until ${snoozedUntil.replace(/</g, "&lt;")}</div>`
            : "";
        const snoozeNotes = (a.snooze_notes || "").trim();
        const snoozeNotesLine = isSnoozed && snoozeNotes
            ? `<div class="compliance-action-snooze-notes">${snoozeNotes.replace(/</g, "&lt;")}</div>`
            : "";

        return `
                <div class="${itemClass} ${status}" data-property-id="${pid}" data-comp-type="${ctype}">
                    <div class="${severityBarClass}" aria-hidden="true"></div>
                    <div class="compliance-action-body compliance-action-body-detail">
                        <div class="compliance-action-top-row">
                            <div class="compliance-action-main">
                                <a class="compliance-action-address" href="${propertyHref}">${propertyText}</a>
                                <div class="compliance-action-type">${typeLabel}</div>
                                <div class="compliance-action-expiry">${displayText}</div>
                            ${snoozedLine}
                            ${snoozeNotesLine}
                            ${liabilityLine}
                            </div>
                            <div class="compliance-action-buttons">
                                <button type="button" class="action-btn-resolve compliance-btn-resolve"${pid ? " " : " disabled "}title="${pid ? "Mark as resolved" : "Property not linked in portal — cannot resolve until this address matches a property record."}">Resolved</button>
                                <button type="button" class="action-btn-snooze compliance-btn-snooze"${pid ? " " : " disabled "}title="${pid ? "Snooze reminders" : "Property not linked in portal."}">Snooze</button>
                                <div class="action-snooze-options">
                                    <button type="button" class="action-btn-snooze-days" data-days="7">1 week</button>
                                    <button type="button" class="action-btn-snooze-days" data-days="14">2 weeks</button>
                                    <button type="button" class="action-btn-snooze-days" data-days="30">1 month</button>
                                    <div class="action-snooze-custom-row">
                                        <input type="number" class="action-snooze-custom-input" min="1" max="730" step="1" placeholder="Days" aria-label="Custom snooze length in days"${pid ? "" : " disabled"} />
                                        <button type="button" class="action-btn-snooze-custom"${pid ? " " : " disabled "}title="${pid ? "Snooze for this many days" : ""}">Custom</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="compliance-action-optional-note">
                            <label class="compliance-action-note-label" for="compliance-action-note-input">Optional note</label>
                            <textarea id="compliance-action-note-input" class="compliance-action-note-input" rows="2" maxlength="2000" placeholder="Comments for your team (saved with resolve or snooze)"${pid ? "" : " disabled"}></textarea>
                        </div>
                    </div>
                </div>
            `;
    }

    function renderComplianceActions(actions) {
        const container = $("#compliance-action-list");
        const detailEl = $("#compliance-action-detail");
        if (!container) return;

        const portalConfig = window.MORPHIQ_COMPLIANCE || {};
        const clientName = portalConfig.clientName || "";

        const source = dedupeComplianceActions(actions || []);
        const filtered = filterComplianceActionsForList(actions);
        const sorted = sortComplianceActionsList(filtered);

        if (!source.length) {
            container.innerHTML = `
                <div class="compliance-success">
                    <div class="compliance-success-icon">✓</div>
                    <div class="compliance-success-text">All certificates are up to date</div>
                    <div class="compliance-success-sub">No expired, expiring, or missing items found.</div>
                </div>
            `;
            if (detailEl) {
                detailEl.innerHTML = `
                    <div class="compliance-detail-empty">
                        <div class="compliance-detail-empty-icon">✓</div>
                        <div>Nothing to review</div>
                    </div>
                `;
            }
            return;
        }

        if (!sorted.length) {
            container.innerHTML = `<div class="empty-state">No actions match these filters.</div>`;
            if (detailEl) {
                detailEl.innerHTML = `
                    <div class="compliance-detail-empty">
                        <div class="compliance-detail-empty-icon">🔍</div>
                        <div>Adjust filters or clear status/type filters to see actions.</div>
                    </div>
                `;
            }
            return;
        }

        let listHtml = "";
        for (let i = 0; i < sorted.length; i++) {
            const a = sorted[i];
            const status = a.status || "";
            const severityBarClass = status === "expired" ? "action-severity-bar expired" : status === "expiring_soon" ? "action-severity-bar expiring" : "action-severity-bar missing";
            const pid = (a.property_id != null) ? String(a.property_id) : "";
            const ctypeRaw = (a.type || "").trim();
            const ctype = ctypeRaw.replace(/"/g, "&quot;");
            const rowKey = complianceActionRowKey(a.property_id, ctypeRaw);
            const isSnoozed = !!a.snoozed;
            const typeLabel = (a.type_label || a.type || "").replace(/</g, "&lt;");
            const propertyText = (a.property || "Unknown property").replace(/</g, "&lt;");
            const displayText = (a.display_text || "").replace(/</g, "&lt;");
            const sel = rowKey === complianceSelectedKey ? " is-selected" : "";
            const snoozedClass = isSnoozed ? " snoozed" : "";
            listHtml += `
                <button type="button" class="compliance-action-row ${status}${snoozedClass}${sel}" data-property-id="${pid}" data-comp-type="${ctype}" aria-pressed="${rowKey === complianceSelectedKey ? "true" : "false"}">
                    <div class="${severityBarClass}" aria-hidden="true"></div>
                    <div class="compliance-action-row-body">
                        <span class="compliance-action-row-address">${propertyText}</span>
                        <span class="compliance-action-row-meta">${typeLabel} · ${displayText}</span>
                    </div>
                </button>
            `;
        }
        container.innerHTML = listHtml;

        const selected = sorted.find((a) => complianceActionRowKey(a.property_id, (a.type || "").trim()) === complianceSelectedKey);
        if (detailEl) {
            if (selected) {
                detailEl.innerHTML = buildComplianceActionCardHtml(selected, clientName);
            } else {
                complianceSelectedKey = "";
                detailEl.innerHTML = `
                    <div class="compliance-detail-empty">
                        <div class="compliance-detail-empty-icon">⚠</div>
                        <div class="compliance-detail-empty-title">Select an action</div>
                        <div>Choose a row in the list to resolve, snooze, or open the property.</div>
                    </div>
                `;
            }
        }
    }

    function renderComplianceStats(stats) {
        const container = $("#compliance-stats");
        if (!container || !stats) return;

        const overdue = stats.overdue_actions || 0;
        const expiring = stats.expiring_soon || 0;
        const missing = stats.missing_certificates || 0;
        const compliant = stats.fully_compliant || 0;
        const total = stats.total_properties || 0;

        container.innerHTML = `
            <div class="compliance-stat-card compliance-stat-overdue">
                <div class="stat-card-inner">
                    <div>
                        <div class="stat-label">Overdue Actions</div>
                        <div class="stat-value">${overdue}</div>
                    </div>
                </div>
            </div>
            <div class="compliance-stat-card compliance-stat-expiring">
                <div class="stat-card-inner">
                    <div>
                        <div class="stat-label">Expiring in 30 Days</div>
                        <div class="stat-value">${expiring}</div>
                    </div>
                </div>
            </div>
            <div class="compliance-stat-card compliance-stat-missing">
                <div class="stat-card-inner">
                    <div>
                        <div class="stat-label">Missing Certificates</div>
                        <div class="stat-value">${missing}</div>
                    </div>
                </div>
            </div>
            <div class="compliance-stat-card compliance-stat-compliant">
                <div class="stat-card-inner">
                    <span class="stat-icon stat-icon-check" aria-hidden="true">✓</span>
                    <div>
                        <div class="stat-label">Fully Compliant</div>
                        <div class="stat-value">${compliant} of ${total}</div>
                    </div>
                </div>
            </div>
        `;

        const bannerEl = $("#compliance-risk-banner");
        if (bannerEl) {
            if (overdue > 0) {
                const exposure = overdue * 6000;
                bannerEl.innerHTML = `Portfolio risk exposure: £${exposure.toLocaleString()} in potential fines across ${overdue} expired certificate${overdue === 1 ? "" : "s"}`;
                bannerEl.style.display = "block";
            } else {
                bannerEl.style.display = "none";
                bannerEl.innerHTML = "";
            }
        }
    }

    function buildComplianceResolvedRowHtml(r, clientName) {
        let propertyHref = "#";
        if (r.property_id) {
            propertyHref = `/property/${r.property_id}`;
            if (clientName) propertyHref += `?client=${encodeURIComponent(clientName)}`;
        }
        const resolvedDate = (r.resolved_at || "").slice(0, 10);
        const by = (r.resolved_by || "").trim() || "—";
        const notes = (r.notes || "").trim();
        const typeLabel = (r.type_label || r.comp_type || "").replace(/</g, "&lt;");
        const propText = (r.property || "—").replace(/</g, "&lt;");
        return `
                <div class="compliance-resolved-item">
                    <a class="compliance-resolved-address" href="${propertyHref}">${propText}</a>
                    <span class="compliance-resolved-type compliance-doc-type-badge">${typeLabel}</span>
                    <span class="compliance-resolved-meta">Resolved by ${(by).replace(/</g, "&lt;")} on ${resolvedDate}${notes ? ` · ${(notes).replace(/</g, "&lt;")}` : ""}</span>
                </div>
            `;
    }

    function buildComplianceSnoozedRowHtml(a, clientName) {
        const pid = a.property_id;
        let propertyHref = "#";
        if (pid != null) {
            propertyHref = `/property/${pid}`;
            if (clientName) propertyHref += `?client=${encodeURIComponent(clientName)}`;
        }
        const until = (a.snoozed_until || "").slice(0, 10);
        const typeLabel = (a.type_label || a.type || "").replace(/</g, "&lt;");
        const propText = (a.property || "—").replace(/</g, "&lt;");
        const displayText = (a.display_text || "").replace(/</g, "&lt;");
        const notes = (a.snooze_notes || "").trim().replace(/</g, "&lt;");
        const metaBits = [`Snoozed until ${until}`];
        if (displayText) metaBits.push(displayText);
        if (notes) metaBits.push(notes);
        return `
                <div class="compliance-snoozed-item">
                    <a class="compliance-snoozed-address" href="${propertyHref}">${propText}</a>
                    <span class="compliance-snoozed-type compliance-doc-type-badge compliance-doc-type-badge--snoozed">${typeLabel}</span>
                    <span class="compliance-snoozed-meta">${metaBits.join(" · ")}</span>
                </div>
            `;
    }

    function renderResolvedSection(resolvedActions, showResolved) {
        const section = $("#compliance-resolved-section");
        const listEl = $("#compliance-resolved-list");
        if (!section || !listEl) return;
        if (!showResolved || !resolvedActions || !resolvedActions.length) {
            section.style.display = "none";
            listEl.innerHTML = "";
            return;
        }
        const cfg = window.MORPHIQ_COMPLIANCE || {};
        const clientName = cfg.clientName || "";
        listEl.innerHTML = resolvedActions.map((r) => buildComplianceResolvedRowHtml(r, clientName)).join("");
        section.style.display = "block";
    }

    function renderComplianceHistoryPane(resolvedActions, actions) {
        const resolvedEl = document.getElementById("compliance-history-resolved-list");
        const snoozedEl = document.getElementById("compliance-history-snoozed-list");
        if (!resolvedEl || !snoozedEl) return;
        const cfg = window.MORPHIQ_COMPLIANCE || {};
        const clientName = cfg.clientName || "";
        const resolved = resolvedActions || [];
        if (!resolved.length) {
            resolvedEl.innerHTML = `<div class="compliance-history-empty">No resolved items for this portfolio.</div>`;
        } else {
            resolvedEl.innerHTML = resolved.map((r) => buildComplianceResolvedRowHtml(r, clientName)).join("");
        }
        const snoozed = (actions || []).filter((a) => a.snoozed && a.snoozed_until);
        snoozed.sort((a, b) => String(a.snoozed_until || "").localeCompare(String(b.snoozed_until || "")));
        if (!snoozed.length) {
            snoozedEl.innerHTML = `<div class="compliance-history-empty">No active snoozes. Snoozed items appear here until the date passes.</div>`;
        } else {
            snoozedEl.innerHTML = snoozed.map((a) => buildComplianceSnoozedRowHtml(a, clientName)).join("");
        }
    }

    const HEALTH_TYPE_LABELS = {
        gas_safety: "Gas Safety (CP12)",
        eicr: "EICR (Electrical)",
        epc: "EPC (Energy)",
        deposit: "Deposit Protection",
    };

    function renderComplianceHealthPanel(healthByType, stats) {
        const panel = $("#compliance-health-panel");
        if (!panel) return;

        if (!healthByType || !healthByType.length) {
            panel.innerHTML = `<div class="compliance-health-empty">No compliance records available.</div>`;
            return;
        }

        const totalProperties = (stats && stats.total_properties) || 0;
        const order = ["gas_safety", "eicr", "epc", "deposit"];
        const sorted = order.map((type) => healthByType.find((h) => h.type === type)).filter(Boolean);

        const rowsHtml = sorted.map((h) => {
            const coveragePct = h.coverage_pct != null ? h.coverage_pct : 0;
            const label = HEALTH_TYPE_LABELS[h.type] || h.label || h.type;
            return `
                <div class="health-panel-row">
                    <span class="health-panel-label">${(label || "").replace(/</g, "&lt;")}</span>
                    <span class="health-panel-pct">${coveragePct}%</span>
                    <div class="health-panel-bar-wrap">
                        <div class="health-panel-bar-fill" style="width:${Math.min(100, coveragePct)}%"></div>
                    </div>
                </div>
            `;
        }).join("");

        let lowest = sorted[0];
        let overallSum = 0;
        sorted.forEach((h) => {
            const pct = h.coverage_pct != null ? h.coverage_pct : 0;
            overallSum += pct;
            if (!lowest || (h.coverage_pct != null && h.coverage_pct < (lowest.coverage_pct ?? 100))) lowest = h;
        });
        const overallPct = sorted.length ? Math.round(overallSum / sorted.length) : 0;
        const lowestLabel = lowest ? (HEALTH_TYPE_LABELS[lowest.type] || lowest.label || lowest.type) : "";
        const needCount = lowest ? (lowest.missing || 0) + (lowest.expired || 0) : 0;
        const belowBench = overallPct < 90 || (lowest && (lowest.coverage_pct ?? 0) < 90);
        const smartText = belowBench && lowestLabel
            ? `Your ${(lowestLabel).replace(/</g, "&lt;")} compliance is below the 90% benchmark. ${needCount} inspection${needCount === 1 ? "" : "s"} recommended this month.`
            : overallPct >= 90
                ? "Portfolio compliance is at or above the 90% benchmark."
                : "Upload certificates to improve coverage.";

        const ringR = 32;
        const ringC = 36;
        const circumference = 2 * Math.PI * ringR;
        const strokeDash = (overallPct / 100) * circumference;

        panel.innerHTML = `
            <div class="health-panel-header">
                <svg class="health-panel-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
                <span>Health by Type</span>
            </div>
            <div class="health-panel-rows">
                ${rowsHtml}
            </div>
            <div class="smart-analysis-card">
                <div class="smart-analysis-ring-wrap">
                    <svg class="smart-analysis-ring" viewBox="0 0 ${ringC * 2} ${ringC * 2}" width="72" height="72">
                        <circle class="smart-analysis-ring-bg" cx="${ringC}" cy="${ringC}" r="${ringR}"/>
                        <circle class="smart-analysis-ring-fill" cx="${ringC}" cy="${ringC}" r="${ringR}" stroke-dasharray="${circumference}" stroke-dashoffset="${circumference - strokeDash}"/>
                    </svg>
                    <span class="smart-analysis-ring-value">${overallPct}%</span>
                </div>
                <p class="smart-analysis-text">${smartText.replace(/</g, "&lt;")}</p>
            </div>
        `;
    }

    function initCompliancePage(uploadModalApi) {
        const root = $("#compliance-root");
        if (!root) return;

        const cfg = window.MORPHIQ_COMPLIANCE || {};
        const clientName = cfg.clientName || "";
        let lastComplianceData = null;

        function complianceUrl() {
            let u = "/api/compliance";
            if (clientName) u += `?client=${encodeURIComponent(clientName)}`;
            return u;
        }

        function refreshCompliance() {
            fetch(complianceUrl())
                .then((res) => res.json())
                .then((data) => {
                    if (!data) return;
                    lastComplianceData = data;
                    renderComplianceStats(data.stats || {});
                    renderComplianceActions(data.actions || []);
                    renderComplianceHealthPanel(data.health_by_type || [], data.stats || {});
                    const showResolved = $("#compliance-show-resolved");
                    renderResolvedSection(data.resolved_actions || [], showResolved ? showResolved.checked : false);
                    renderComplianceHistoryPane(data.resolved_actions || [], data.actions || []);
                })
                .catch((err) => {
                    console.error("Failed to load compliance data:", err);
                    const actions = $("#compliance-action-list");
                    if (actions) actions.innerHTML = `<div class="deadline-sub">Failed to load compliance data.</div>`;
                });
        }

        function complianceActionNoteValue(item) {
            const ta = item.querySelector(".compliance-action-note-input");
            return ta ? String(ta.value || "").trim() : "";
        }

        function submitComplianceResolve(item, notes) {
            const propertyId = item.getAttribute("data-property-id");
            const compType = (item.getAttribute("data-comp-type") || "").trim();
            if (!propertyId || !compType) {
                alert(
                    "This action cannot be resolved because the property is not linked in the portal (no property ID). Sync from Review Station or ensure the address matches a property record.",
                );
                return;
            }
            const pidNum = parseInt(propertyId, 10);
            if (!Number.isFinite(pidNum)) {
                alert("Invalid property ID for this action.");
                return;
            }
            item.classList.add("action-item-resolving");
            const resolveBtn = item.querySelector(".action-btn-resolve");
            fetch("/api/compliance/actions/resolve", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify({ property_id: pidNum, comp_type: compType, notes: notes || "" }),
            })
                .then(async (res) => {
                    if (!res.ok) {
                        let msg = "Resolve failed";
                        try {
                            const j = await res.json();
                            if (j && j.error) msg = j.error;
                        } catch (_) {}
                        throw new Error(msg);
                    }
                    item.classList.remove("action-item-resolving");
                    item.classList.add("action-item-resolved-out");
                    let done = false;
                    const onTransitionEnd = () => {
                        if (done) return;
                        done = true;
                        item.removeEventListener("transitionend", onTransitionEnd);
                        refreshCompliance();
                    };
                    item.addEventListener("transitionend", onTransitionEnd);
                    setTimeout(onTransitionEnd, 350);
                })
                .catch((err) => {
                    console.error(err);
                    item.classList.remove("action-item-resolving");
                    const msg = err && err.message ? err.message : "Resolve failed";
                    alert(msg);
                    showButtonError(resolveBtn, "Resolved");
                });
        }

        function submitComplianceSnooze(item, days) {
            const propertyId = item.getAttribute("data-property-id");
            const compType = (item.getAttribute("data-comp-type") || "").trim();
            if (!propertyId || !compType) {
                alert(
                    "This action cannot be snoozed because the property is not linked in the portal (no property ID).",
                );
                return;
            }
            const pidNum = parseInt(propertyId, 10);
            if (!Number.isFinite(pidNum)) {
                alert("Invalid property ID for this action.");
                return;
            }
            const d = Number(days);
            if (!Number.isFinite(d) || d < 1 || d > 730 || Math.floor(d) !== d) {
                alert("Enter a whole number of days between 1 and 730.");
                return;
            }
            const opts = item.querySelector(".action-snooze-options");
            if (opts) opts.classList.remove("is-open");
            const snoozeBtn = item.querySelector(".action-btn-snooze");
            item.classList.add("action-item-resolving");
            fetch("/api/compliance/actions/snooze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify({
                    property_id: pidNum,
                    comp_type: compType,
                    days: d,
                    notes: complianceActionNoteValue(item),
                }),
            })
                .then(async (res) => {
                    if (!res.ok) {
                        let msg = "Snooze failed";
                        try {
                            const j = await res.json();
                            if (j && j.error) msg = j.error;
                        } catch (_) {}
                        throw new Error(msg);
                    }
                    item.classList.remove("action-item-resolving");
                    item.classList.add("action-item-resolved-out");
                    let done = false;
                    const onTransitionEnd = () => {
                        if (done) return;
                        done = true;
                        item.removeEventListener("transitionend", onTransitionEnd);
                        refreshCompliance();
                    };
                    item.addEventListener("transitionend", onTransitionEnd);
                    setTimeout(onTransitionEnd, 350);
                })
                .catch((err) => {
                    console.error(err);
                    item.classList.remove("action-item-resolving");
                    const msg = err && err.message ? err.message : "Snooze failed";
                    alert(msg);
                    showButtonError(snoozeBtn, "Snooze");
                });
        }

        // Export Report button
        const complianceExportBtn = $("#compliance-export-report");
        if (complianceExportBtn) {
            complianceExportBtn.addEventListener("click", () => {
                const client = (cfg.clientName || "").trim() || (new URLSearchParams(window.location.search).get("client") || "");
                const url = "/api/compliance/report?format=pdf" + (client ? "&client=" + encodeURIComponent(client) : "");
                if (!client) {
                    alert("Please select a client first.");
                    return;
                }
                downloadReportPdf(url, complianceExportBtn, "Export");
            });
        }

        // Upload Document button
        const complianceUploadBtn = $("#compliance-upload-document");
        if (complianceUploadBtn && uploadModalApi) {
            complianceUploadBtn.addEventListener("click", async () => {
                let url = "/api/properties";
                if (clientName) url += `?client=${encodeURIComponent(clientName)}`;
                try {
                    const res = await fetch(url);
                    const data = await res.json().catch(() => ({}));
                    uploadModalApi.openUploadModal({ propertyList: (data && data.properties) || [] });
                } catch (err) {
                    console.error("Failed to load properties:", err);
                    uploadModalApi.openUploadModal({ propertyList: [] });
                }
            });
        }

        document.querySelectorAll(".compliance-workspace-mode-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                const mode = btn.getAttribute("data-compliance-workspace");
                if (mode) setComplianceWorkspaceMode(mode);
            });
        });

        const typeChips = document.getElementById("compliance-type-chips");
        if (typeChips) {
            typeChips.addEventListener("click", (e) => {
                const chip = e.target.closest(".filter-chip[data-compliance-filter]");
                if (!chip) return;
                complianceTypeFilter = chip.getAttribute("data-compliance-filter") || "all";
                typeChips.querySelectorAll(".filter-chip").forEach((c) => {
                    c.classList.toggle("active", c.getAttribute("data-compliance-filter") === complianceTypeFilter);
                });
                complianceSelectedKey = "";
                setComplianceWorkspaceMode("health");
                if (lastComplianceData) renderComplianceActions(lastComplianceData.actions || []);
            });
        }

        const severityEl = document.getElementById("compliance-severity-filter");
        if (severityEl) {
            severityEl.addEventListener("change", () => {
                complianceSeverityFilter = severityEl.value || "all";
                complianceSelectedKey = "";
                setComplianceWorkspaceMode("health");
                if (lastComplianceData) renderComplianceActions(lastComplianceData.actions || []);
            });
        }

        function showButtonError(btn, originalText) {
            if (!btn) return;
            const orig = originalText || btn.textContent;
            btn.textContent = "Failed — try again";
            btn.classList.add("action-failed");
            setTimeout(() => {
                btn.textContent = orig;
                btn.classList.remove("action-failed");
            }, 2500);
        }

        const actionDetailEl = document.getElementById("compliance-action-detail");
        if (actionDetailEl) {
            actionDetailEl.addEventListener(
                "click",
                (e) => {
                    const item = e.target.closest(".compliance-action-card");
                    if (!item) return;

                    const propertyId = item.getAttribute("data-property-id");
                    const compType = (item.getAttribute("data-comp-type") || "").trim();
                    if (!propertyId || !compType) {
                        alert(
                            "This action is missing a property or certificate type. It cannot be updated from here.",
                        );
                        return;
                    }

                    if (e.target.closest(".action-btn-resolve")) {
                        const resolveBtnEl = e.target.closest(".action-btn-resolve");
                        if (resolveBtnEl && resolveBtnEl.disabled) return;
                        e.preventDefault();
                        e.stopPropagation();
                        submitComplianceResolve(item, complianceActionNoteValue(item));
                        return;
                    }
                    if (e.target.closest(".action-btn-snooze")) {
                        e.preventDefault();
                        e.stopPropagation();
                        const opts = item.querySelector(".action-snooze-options");
                        const form = item.querySelector(".action-resolve-form");
                        const isOpen = opts && opts.classList.contains("is-open");
                        root.querySelectorAll(".action-snooze-options.is-open").forEach((o) => o.classList.remove("is-open"));
                        if (opts) opts.classList.toggle("is-open", !isOpen);
                        if (form) form.style.display = "none";
                        if (!opts || !opts.classList.contains("is-open")) return;
                        const closeSnooze = (ev) => {
                            if (opts && opts.contains(ev && ev.target)) return;
                            if (opts) opts.classList.remove("is-open");
                            document.removeEventListener("click", closeSnooze);
                        };
                        setTimeout(() => document.addEventListener("click", closeSnooze), 0);
                        return;
                    }
                    if (e.target.closest(".action-btn-snooze-days")) {
                        e.preventDefault();
                        e.stopPropagation();
                        const dayBtn = e.target.closest(".action-btn-snooze-days");
                        const days = parseInt(dayBtn && dayBtn.getAttribute("data-days"), 10);
                        if (!Number.isFinite(days)) return;
                        submitComplianceSnooze(item, days);
                        return;
                    }
                    if (e.target.closest(".action-btn-snooze-custom")) {
                        e.preventDefault();
                        e.stopPropagation();
                        const customBtn = e.target.closest(".action-btn-snooze-custom");
                        if (customBtn && customBtn.disabled) return;
                        const input = item.querySelector(".action-snooze-custom-input");
                        const raw = input ? String(input.value || "").trim() : "";
                        const days = parseInt(raw, 10);
                        submitComplianceSnooze(item, days);
                    }
                },
                true,
            );
            actionDetailEl.addEventListener("keydown", (e) => {
                if (e.key !== "Enter") return;
                const input = e.target.closest(".action-snooze-custom-input");
                if (!input || input.disabled) return;
                const item = input.closest(".compliance-action-card");
                if (!item) return;
                e.preventDefault();
                e.stopPropagation();
                const raw = String(input.value || "").trim();
                const days = parseInt(raw, 10);
                submitComplianceSnooze(item, days);
            });
        }

        root.addEventListener("click", (e) => {
            const row = e.target.closest(".compliance-action-row");
            if (row) {
                const propertyId = row.getAttribute("data-property-id");
                const compTypeAttr = row.getAttribute("data-comp-type") || "";
                if (!propertyId || !compTypeAttr) return;
                complianceSelectedKey = complianceActionRowKey(propertyId, compTypeAttr);
                setComplianceWorkspaceMode("action");
                if (lastComplianceData) renderComplianceActions(lastComplianceData.actions || []);
            }
        });

        // Show resolved toggle
        const showResolvedEl = $("#compliance-show-resolved");
        if (showResolvedEl) {
            showResolvedEl.addEventListener("change", () => {
                if (!lastComplianceData) return;
                renderResolvedSection(lastComplianceData.resolved_actions || [], showResolvedEl.checked);
            });
        }

        refreshCompliance();
    }

    // ── Chat / MorphIQ Intelligence ─────────────────────────────────────────
    function initChat() {
        const input = document.getElementById("ai-chat-input");
        const sendBtn = document.getElementById("ai-chat-send");
        const floatBtn = document.getElementById("ai-chat-float-btn");
        const floatUnread = document.getElementById("ai-chat-float-unread");
        const sidebar = document.getElementById("ai-chat-sidebar");
        const backdrop = document.getElementById("ai-chat-sidebar-backdrop");
        const sidebarClose = document.getElementById("ai-chat-sidebar-close");
        const sidebarBack = document.getElementById("ai-chat-sidebar-back");
        const listView = document.getElementById("ai-chat-sidebar-list-view");
        const chatView = document.getElementById("ai-chat-sidebar-chat-view");
        const conversationListEl = document.getElementById("ai-chat-conversation-list");
        const newConvBtn = document.getElementById("ai-chat-new-conv-btn");
        const chatTitleEl = document.getElementById("ai-chat-sidebar-chat-title");
        const messageListEl = document.getElementById("ai-chat-message-list");
        const suggestionsEl = document.getElementById("ai-chat-suggestions");
        const messagesEl = document.getElementById("ai-chat-sidebar-messages");

        if (!input || !sendBtn || !floatBtn || !sidebar || !backdrop) return;

        chatClientName = getClientForNotifications();
        function getClientParam() {
            return chatClientName || "";
        }

        migrateChatHistoryToConversations();

        function openSidebar() {
            chatSidebarOpen = true;
            if (backdrop) backdrop.classList.add("is-open");
            if (backdrop) backdrop.setAttribute("aria-hidden", "false");
            if (sidebar) sidebar.classList.add("is-open");
            if (floatBtn) floatBtn.style.display = "none";
            chatHasUnreadSinceMinimize = false;
            updateUnreadIndicator();
            try { localStorage.setItem(CHAT_OPEN_KEY, "true"); } catch (_) {}
        }

        function closeSidebar() {
            chatSidebarOpen = false;
            if (backdrop) backdrop.classList.remove("is-open");
            if (backdrop) backdrop.setAttribute("aria-hidden", "true");
            if (sidebar) sidebar.classList.remove("is-open");
            if (floatBtn) floatBtn.style.display = "flex";
            try { localStorage.setItem(CHAT_OPEN_KEY, "false"); } catch (_) {}
        }

        function updateUnreadIndicator() {
            if (!floatUnread) return;
            if (chatHasUnreadSinceMinimize && !chatSidebarOpen) {
                floatUnread.classList.add("has-unread");
            } else {
                floatUnread.classList.remove("has-unread");
            }
        }

        function showListView() {
            currentConversationId = null;
            if (listView) listView.classList.remove("hidden");
            if (chatView) chatView.classList.add("hidden");
            renderConversationList();
        }

        function showChatView() {
            if (listView) listView.classList.add("hidden");
            if (chatView) chatView.classList.remove("hidden");
        }

        function relativeTime(iso) {
            if (!iso) return "";
            const d = new Date(iso);
            if (isNaN(d)) return "";
            const now = new Date();
            const diffMs = now - d;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMs / 3600000);
            const diffDays = Math.floor(diffMs / 86400000);
            if (diffMins < 1) return "Just now";
            if (diffMins < 60) return diffMins + " min ago";
            if (diffHours < 24) return diffHours + " hour" + (diffHours === 1 ? "" : "s") + " ago";
            if (diffDays === 1) return "Yesterday";
            if (diffDays < 7) return diffDays + " days ago";
            return d.toLocaleDateString();
        }

        function renderConversationList() {
            if (!conversationListEl) return;
            const convos = getConversations().sort((a, b) =>
                new Date(b.updated_at || 0) - new Date(a.updated_at || 0));
            if (convos.length === 0) {
                conversationListEl.innerHTML = `<div class="ai-chat-conv-empty" style="padding:12px;color:var(--text-muted);font-size:13px;">No conversations yet. Start a new one below.</div>`;
                return;
            }
            conversationListEl.innerHTML = convos.map((c) => {
                const title = (c.title || "New conversation").replace(/</g, "&lt;");
                const time = relativeTime(c.updated_at || c.created_at);
                return `<button type="button" class="ai-chat-conv-card" data-conv-id="${(c.id || "").replace(/"/g, "&quot;")}">
                    <div class="ai-chat-conv-card-title">${title}</div>
                    <div class="ai-chat-conv-card-time">${time}</div>
                </button>`;
            }).join("");
            conversationListEl.querySelectorAll(".ai-chat-conv-card").forEach((btn) => {
                btn.addEventListener("click", () => {
                    const id = btn.getAttribute("data-conv-id");
                    if (!id) return;
                    openConversation(id);
                });
            });
        }

        function openConversation(id) {
            const convos = getConversations();
            const conv = convos.find((c) => c.id === id);
            if (!conv) return;
            currentConversationId = id;
            chatMessages = Array.isArray(conv.messages) ? [...conv.messages] : [];
            if (chatTitleEl) chatTitleEl.textContent = (conv.title || "Chat").slice(0, 50);
            showChatView();
            renderChat();
        }

        function newConversation() {
            const id = "conv-" + Date.now() + "-" + Math.random().toString(36).slice(2, 9);
            const now = new Date().toISOString();
            const conv = { id, title: "New conversation", messages: [], created_at: now, updated_at: now };
            const convos = getConversations();
            convos.unshift(conv);
            saveConversations(convos);
            currentConversationId = id;
            chatMessages = [];
            if (chatTitleEl) chatTitleEl.textContent = "New conversation";
            showChatView();
            renderChat();
        }

        function persistCurrentConversation() {
            if (!currentConversationId) return;
            const convos = getConversations();
            const idx = convos.findIndex((c) => c.id === currentConversationId);
            if (idx === -1) return;
            convos[idx].messages = chatMessages.slice(-CHAT_HISTORY_MAX);
            convos[idx].updated_at = new Date().toISOString();
            if (chatMessages.length > 0) {
                const firstUser = (chatMessages[0].user || "").trim();
                convos[idx].title = firstUser.length > 40 ? firstUser.slice(0, 37) + "…" : firstUser || "New conversation";
            }
            saveConversations(convos);
            if (chatTitleEl && convos[idx].title) chatTitleEl.textContent = convos[idx].title.slice(0, 50);
            renderConversationList();
        }

        floatBtn.addEventListener("click", () => {
            openSidebar();
            if (currentConversationId) showChatView();
            else showListView();
        });
        if (backdrop) backdrop.addEventListener("click", closeSidebar);
        if (sidebarClose) sidebarClose.addEventListener("click", closeSidebar);
        if (sidebarBack) sidebarBack.addEventListener("click", () => { showListView(); });
        if (newConvBtn) newConvBtn.addEventListener("click", newConversation);

        function scrollMessagesToBottom() {
            if (!messagesEl) return;
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }

        function escapeHtml(text) {
            return (text || "")
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;");
        }

        /** Parse [[text|ID]], [[text|ID:TYPE]], **bold**, and newlines; render as clickable .chat-link and <strong>; preserve ?client= */
        function parsePropertyLinks(text, clientParam) {
            let s = (text || "");
            const linkList = [];
            // [[label|ID:TYPE]] first (more specific)
            s = s.replace(/\[\[([^\]|]+)\|(\d+):([^\]]+)\]\]/g, (match, label, id, type) => {
                linkList.push({ label: label.trim(), id, type: type.trim() });
                return "\x00L" + (linkList.length - 1) + "L\x00";
            });
            // [[label|ID]]
            s = s.replace(/\[\[([^\]|]+)\|(\d+)\]\]/g, (match, label, id) => {
                linkList.push({ label: label.trim(), id, type: null });
                return "\x00L" + (linkList.length - 1) + "L\x00";
            });
            // **bold**
            s = s.replace(/\*\*([^*]+)\*\*/g, "\x00B\x00$1\x00/B\x00");
            s = escapeHtml(s);
            s = s.replace(/\x00B\x00/g, "<strong>").replace(/\x00\/B\x00/g, "</strong>");
            linkList.forEach((l, i) => {
                let href = "/property/" + l.id;
                const params = [];
                if (l.type) params.push("focus=" + encodeURIComponent(l.type));
                if (clientParam) params.push("client=" + encodeURIComponent(clientParam));
                if (params.length) href += "?" + params.join("&");
                const safeHref = href.replace(/&/g, "&amp;").replace(/"/g, "&quot;");
                s = s.replace("\x00L" + i + "L\x00", '<a class="chat-link" href="' + safeHref + '">' + escapeHtml(l.label) + "</a>");
            });
            return s.split("\n").join("<br>");
        }

        function formatMessageTime(isoOrDate) {
            if (!isoOrDate) return "";
            const d = new Date(isoOrDate);
            if (isNaN(d)) return "";
            return d.toTimeString().slice(0, 5);
        }

        function renderChat() {
            if (!messageListEl || !suggestionsEl) return;

            if (chatMessages.length === 0) {
                messageListEl.innerHTML = "";
                messageListEl.style.display = "none";
                suggestionsEl.style.display = "flex";
                return;
            }

            suggestionsEl.style.display = "none";
            messageListEl.style.display = "block";

            const clientParam = getClientParam();
            const pairsHtml = chatMessages
                .map((pair) => {
                    const userTimeStr = formatMessageTime(pair.timestamp);
                    const assistantTimeStr = formatMessageTime(pair.assistantTimestamp || pair.timestamp);
                    const assistantRaw = pair.assistant || "";
                    const assistantHtml = parsePropertyLinks(assistantRaw, clientParam);
                    const userHtml = escapeHtml(pair.user || "");
                    const assistantClass = pair.isError
                        ? "ai-chat-message-assistant error"
                        : "ai-chat-message-assistant";
                    return `
                        <div class="ai-chat-message-pair">
                            <div class="ai-chat-message-user-wrap">
                                <span class="ai-chat-message-time">${escapeHtml(userTimeStr)}</span>
                                <div class="ai-chat-message-user">${userHtml}</div>
                            </div>
                            <div class="ai-chat-message-assistant-wrap">
                                <span class="ai-chat-message-time">${escapeHtml(assistantTimeStr)}</span>
                                <div class="${assistantClass}">${assistantHtml}</div>
                            </div>
                        </div>
                    `;
                })
                .join("");

            messageListEl.innerHTML = pairsHtml;
            scrollMessagesToBottom();
        }

        function setLoadingForLastPair() {
            if (!messageListEl || !chatMessages.length) return;

            suggestionsEl.style.display = "none";
            messageListEl.style.display = "block";

            const clientParam = getClientParam();
            const previousPairs = chatMessages.slice(0, -1);
            const lastPair = chatMessages[chatMessages.length - 1];

            const previousHtml = previousPairs
                .map((pair) => {
                    const userTimeStr = formatMessageTime(pair.timestamp);
                    const assistantTimeStr = formatMessageTime(pair.assistantTimestamp || pair.timestamp);
                    const assistantRaw = pair.assistant || "";
                    const assistantHtml = parsePropertyLinks(assistantRaw, clientParam);
                    const userHtml = escapeHtml(pair.user || "");
                    const assistantClass = pair.isError
                        ? "ai-chat-message-assistant error"
                        : "ai-chat-message-assistant";
                    return `
                        <div class="ai-chat-message-pair">
                            <div class="ai-chat-message-user-wrap">
                                <span class="ai-chat-message-time">${escapeHtml(userTimeStr)}</span>
                                <div class="ai-chat-message-user">${userHtml}</div>
                            </div>
                            <div class="ai-chat-message-assistant-wrap">
                                <span class="ai-chat-message-time">${escapeHtml(assistantTimeStr)}</span>
                                <div class="${assistantClass}">${assistantHtml}</div>
                            </div>
                        </div>
                    `;
                })
                .join("");

            const userTimeStr = formatMessageTime(lastPair.timestamp);
            const lastUserHtml = escapeHtml(lastPair.user || "");
            const loadingHtml = `
                <div class="ai-chat-message-pair">
                    <div class="ai-chat-message-user-wrap">
                        <span class="ai-chat-message-time">${escapeHtml(userTimeStr)}</span>
                        <div class="ai-chat-message-user">${lastUserHtml}</div>
                    </div>
                    <div class="ai-chat-message-assistant-wrap">
                        <span class="ai-chat-message-time">${escapeHtml(userTimeStr)}</span>
                        <div class="ai-chat-message-assistant">
                            <span class="ai-chat-loading-dots">
                                <span></span><span></span><span></span>
                            </span>
                        </div>
                    </div>
                </div>
            `;

            messageListEl.innerHTML = previousHtml + loadingHtml;
            scrollMessagesToBottom();
        }

        function addMessage(userText, assistantText) {
            if (!userText) return;
            const trimmedUser = userText.trim();
            if (!trimmedUser) return;
            if (!currentConversationId) newConversation();
            const pair = {
                user: trimmedUser,
                assistant: assistantText || "",
                isError: false,
                timestamp: new Date().toISOString(),
            };
            chatMessages.push(pair);
            if (chatMessages.length > CHAT_HISTORY_MAX) {
                chatMessages = chatMessages.slice(-CHAT_HISTORY_MAX);
            }
            persistCurrentConversation();
            renderChat();
        }

        async function sendChatMessage(rawText) {
            const text = (rawText || "").trim();
            if (!text || chatRequestInFlight) return;

            const clientName = getClientParam();

            addMessage(text, "");
            setLoadingForLastPair();

            chatRequestInFlight = true;
            sendBtn.disabled = true;

            try {
                const url = "/api/chat";
                const options = {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        message: text,
                        client: clientName || "",
                    }),
                };
                const res = await fetch(url, options);

                let responseText = "";
                if (res.ok) {
                    const data = await res.json().catch(() => ({}));
                    responseText = (data && data.response) || "";
                } else {
                    responseText =
                        "Unable to connect to Morph IQ Intelligence. Please try again.";
                }

                if (!responseText) {
                    responseText =
                        "Unable to connect to Morph IQ Intelligence. Please try again.";
                }

                if (chatMessages.length) {
                    chatMessages[chatMessages.length - 1].assistant = responseText;
                    chatMessages[chatMessages.length - 1].assistantTimestamp = new Date().toISOString();
                    chatMessages[chatMessages.length - 1].isError = false;
                }
                if (chatMessages.length > CHAT_HISTORY_MAX) {
                    chatMessages = chatMessages.slice(-CHAT_HISTORY_MAX);
                }
                persistCurrentConversation();
                renderChat();
                if (!chatSidebarOpen) {
                    chatHasUnreadSinceMinimize = true;
                    updateUnreadIndicator();
                }
            } catch (err) {
                console.error("Chat error:", err);
                const errorText =
                    "Unable to connect to Morph IQ Intelligence. Please try again.";
                if (chatMessages.length) {
                    chatMessages[chatMessages.length - 1].assistant = errorText;
                    chatMessages[chatMessages.length - 1].isError = true;
                }
                persistCurrentConversation();
                renderChat();
                if (!chatSidebarOpen) {
                    chatHasUnreadSinceMinimize = true;
                    updateUnreadIndicator();
                }
            } finally {
                chatRequestInFlight = false;
                sendBtn.disabled = false;
            }
        }

        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                const value = input.value;
                if (!value.trim()) return;
                input.value = "";
                sendChatMessage(value);
            }
        });

        sendBtn.addEventListener("click", () => {
            const value = input.value;
            if (!value.trim()) return;
            input.value = "";
            sendChatMessage(value);
        });

        document.querySelectorAll(".ai-chat-chip").forEach((chip) => {
            chip.addEventListener("click", () => {
                const question = chip.getAttribute("data-question");
                if (question) {
                    sendChatMessage(question);
                    return;
                }
                const tpl = chip.getAttribute("data-template");
                let text = "";
                if (tpl === "summary") {
                    text = "Give me a portfolio compliance summary with key numbers and urgent actions";
                } else if (tpl === "missing") {
                    text = "Which properties are missing required certificates? List each one with what's missing.";
                }
                if (text) sendChatMessage(text);
            });
        });

        if (suggestionsEl) {
            suggestionsEl
                .querySelectorAll(".ai-chat-suggestion-pill")
                .forEach((pill) => {
                    pill.addEventListener("click", () => {
                        const q =
                            pill.getAttribute("data-question") ||
                            pill.textContent ||
                            "";
                        if (!q) return;
                        sendChatMessage(q);
                    });
                });
        }

        const savedOpen = (function () {
            try { return localStorage.getItem(CHAT_OPEN_KEY); } catch (_) { return null; }
        })();
        if (savedOpen === "true") {
            openSidebar();
            showListView();
        }
        updateUnreadIndicator();

        const totalMessages = getConversations().reduce((n, c) => n + (Array.isArray(c.messages) ? c.messages.length : 0), 0);
        if (floatBtn && totalMessages === 0) {
            floatBtn.classList.add("ai-chat-float-btn-pulse");
            setTimeout(() => {
                if (floatBtn) floatBtn.classList.remove("ai-chat-float-btn-pulse");
            }, 5000);
        }

        document.addEventListener("keydown", (e) => {
            if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return;
            const active = document.activeElement;
            const tag = active ? (active.tagName || "").toLowerCase() : "";
            const isInput = tag === "input" || tag === "textarea" || (active && active.isContentEditable);
            if (isInput) return;
            e.preventDefault();
            openSidebar();
            if (currentConversationId) {
                showChatView();
                setTimeout(() => { if (input) input.focus(); }, 50);
            } else {
                showListView();
            }
        });
    }

    // ── Full-page AI chat (/ask-ai) ────────────────────────────────────────
    function initAiChatPage() {
        const messagesEl = document.getElementById("ai-chat-page-messages");
        const form = document.getElementById("ai-chat-page-form");
        const input = document.getElementById("ai-chat-page-input");
        const sendBtn = document.getElementById("ai-chat-page-send");
        const welcomeEl = document.getElementById("ai-chat-welcome");
        const clearBtn = document.getElementById("ai-chat-clear-chat");
        const scrollRoot =
            document.querySelector(".ask-ai-scroll") || messagesEl.parentElement || messagesEl;
        if (!messagesEl || !form || !input || !sendBtn) return;

        const clientName =
            (window.MORPHIQ_PORTAL && window.MORPHIQ_PORTAL.clientName) || "";

        function scrollToBottom() {
            if (scrollRoot && scrollRoot.scrollHeight != null) {
                scrollRoot.scrollTop = scrollRoot.scrollHeight;
            } else {
                messagesEl.scrollTop = messagesEl.scrollHeight;
            }
        }

        function createMessageElement(role, text, metaText, extraClass) {
            if (role === "user") {
                const row = document.createElement("div");
                row.className = "ai-chat-msg-row ai-chat-msg-row-user";
                const bubble = document.createElement("div");
                bubble.className = "ai-chat-bubble ai-chat-bubble-user";
                const body = document.createElement("div");
                body.className = "ai-chat-message-text";
                body.textContent = text;
                bubble.appendChild(body);
                if (metaText) {
                    const meta = document.createElement("div");
                    meta.className = "ai-chat-message-meta ai-chat-message-meta-user";
                    meta.textContent = metaText;
                    bubble.appendChild(meta);
                }
                row.appendChild(bubble);
                return row;
            }

            const row = document.createElement("div");
            row.className =
                "ai-chat-msg-row ai-chat-msg-row-assistant" +
                (extraClass === "ai-chat-message-loading" ? " ai-chat-row-loading" : "");

            const avatar = document.createElement("div");
            avatar.className = "ai-chat-assistant-avatar";
            avatar.setAttribute("aria-hidden", "true");
            avatar.innerHTML =
                '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>';

            const col = document.createElement("div");
            col.className = "ai-chat-assistant-col";

            const bubble = document.createElement("div");
            bubble.className =
                "ai-chat-bubble ai-chat-bubble-assistant" +
                (extraClass === "ai-chat-message-loading" ? " ai-chat-bubble-loading" : "") +
                (extraClass && extraClass !== "ai-chat-message-loading" ? " " + extraClass : "");

            const body = document.createElement("div");
            body.className = "ai-chat-message-text";
            body.textContent = text;
            bubble.appendChild(body);

            if (extraClass !== "ai-chat-message-loading") {
                const cards = document.createElement("div");
                cards.className = "ai-chat-result-cards";
                cards.setAttribute("aria-hidden", "true");
                bubble.appendChild(cards);
            }

            if (metaText) {
                const meta = document.createElement("div");
                meta.className = "ai-chat-message-meta ai-chat-message-meta-assistant";
                meta.textContent = metaText;
                bubble.appendChild(meta);
            }

            col.appendChild(bubble);
            row.appendChild(avatar);
            row.appendChild(col);
            return row;
        }

        function appendMessageEl(el) {
            messagesEl.appendChild(el);
            scrollToBottom();
        }

        function loadAskAiStats() {
            fetch(withClientQuery("/api/dashboard-stats"), { credentials: "same-origin" })
                .then((r) => r.json())
                .then((d) => {
                    if (!d || d.error) return;
                    const p = document.getElementById("ai-chat-count-props");
                    const doc = document.getElementById("ai-chat-count-docs");
                    const hint = document.getElementById("ai-chat-doc-indexed-hint");
                    const tp = d.total_properties != null ? String(d.total_properties) : "—";
                    const td = d.total_documents != null ? String(d.total_documents) : "—";
                    if (p) p.textContent = tp;
                    if (doc) doc.textContent = td;
                    if (hint) hint.textContent = `${td === "—" ? "0" : td} documents indexed`;
                })
                .catch(() => {});
        }
        loadAskAiStats();

        if (clearBtn) {
            clearBtn.addEventListener("click", () => {
                messagesEl.innerHTML = "";
                if (welcomeEl) welcomeEl.hidden = false;
                scrollToBottom();
                input.focus();
            });
        }

        document.querySelectorAll(".ai-chat-suggestion-card").forEach((btn) => {
            btn.addEventListener("click", () => {
                const q = (btn.getAttribute("data-query") || "").trim();
                if (!q || !input) return;
                input.value = q;
                form.requestSubmit();
            });
        });

        async function sendMessage(message) {
            if (welcomeEl) welcomeEl.hidden = true;

            const userTime = new Date().toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
            });
            appendMessageEl(createMessageElement("user", message, "You · " + userTime));

            const loadingEl = createMessageElement(
                "assistant",
                "MorphIQ AI is thinking…",
                "",
                "ai-chat-message-loading"
            );
            appendMessageEl(loadingEl);

            input.disabled = true;
            sendBtn.disabled = true;

            try {
                const res = await fetch("/api/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    credentials: "same-origin",
                    body: JSON.stringify({
                        message,
                        client: clientName || undefined,
                    }),
                });
                const data = await res.json().catch(() => ({}));
                if (loadingEl.parentNode === messagesEl) {
                    messagesEl.removeChild(loadingEl);
                }

                if (!res.ok || !data || typeof data.response !== "string") {
                    const errText =
                        (data && data.error) ||
                        "Unable to get a response from MorphIQ AI.";
                    appendMessageEl(
                        createMessageElement(
                            "assistant",
                            errText,
                            "",
                            "ai-chat-message-error"
                        )
                    );
                    return;
                }

                const assistantTime = new Date().toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                });
                appendMessageEl(
                    createMessageElement(
                        "assistant",
                        data.response,
                        "MorphIQ AI · " + assistantTime
                    )
                );
            } catch (err) {
                if (loadingEl.parentNode === messagesEl) {
                    messagesEl.removeChild(loadingEl);
                }
                appendMessageEl(
                    createMessageElement(
                        "assistant",
                        "Error contacting MorphIQ AI. Please try again.",
                        "",
                        "ai-chat-message-error"
                    )
                );
            } finally {
                input.disabled = false;
                sendBtn.disabled = false;
                input.focus();
            }
        }

        form.addEventListener("submit", (e) => {
            e.preventDefault();
            const value = (input.value || "").trim();
            if (!value) return;
            input.value = "";
            sendMessage(value);
        });

        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                form.dispatchEvent(new Event("submit", { cancelable: true }));
            }
        });
    }

    function initUploadModal() {
        const UPLOAD_ALLOWED_EXT = [".pdf", ".jpg", ".jpeg", ".png", ".tiff"];
        const UPLOAD_MAX_BYTES = 20 * 1024 * 1024; // 20MB

        function isUploadAllowed(filename) {
            const ext = filename.slice(filename.lastIndexOf(".")).toLowerCase();
            return UPLOAD_ALLOWED_EXT.includes(ext);
        }

        function closeUploadModal() {
            const modal = $("#upload-document-modal");
            if (modal) {
                modal.classList.add("hidden");
                modal.setAttribute("aria-hidden", "true");
            }
            const form = $("#upload-document-form");
            if (form) form.reset();
            const errEl = $("#upload-file-error");
            if (errEl) {
                errEl.textContent = "";
                errEl.classList.add("hidden");
            }
            const dropPrompt = $("#upload-dropzone-prompt");
            const dropFilename = $("#upload-dropzone-filename");
            if (dropPrompt) dropPrompt.classList.remove("hidden");
            if (dropFilename) {
                dropFilename.textContent = "";
                dropFilename.classList.add("hidden");
            }
            const submitBtn = $("#upload-modal-submit");
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = "Upload";
            }
        }

        function showUploadToast(message) {
            const toast = $("#upload-toast");
            if (!toast) return;
            toast.textContent = message;
            toast.classList.remove("hidden");
            toast.classList.add("upload-toast-visible");
            setTimeout(() => {
                toast.classList.remove("upload-toast-visible");
                setTimeout(() => toast.classList.add("hidden"), 300);
            }, 4000);
        }

        function openUploadModal(opts) {
            opts = opts || {};
            const propertyField = $("#upload-property-field");
            const propertySelect = $("#upload-property-select");
            const docTypeEl = $("#upload-doc-type");

            if (opts.propertyList !== undefined && propertySelect) {
                if (propertyField) propertyField.classList.remove("hidden");
                propertySelect.innerHTML = "";
                const placeholder = document.createElement("option");
                placeholder.value = "";
                placeholder.textContent = opts.propertyList.length ? "Select property…" : "No properties found";
                propertySelect.appendChild(placeholder);
                (opts.propertyList || []).forEach((p) => {
                    const opt = document.createElement("option");
                    opt.value = String(p.property_id);
                    opt.textContent = p.property_address || p.address || `Property ${p.property_id}`;
                    propertySelect.appendChild(opt);
                });
            } else if (propertyField) {
                propertyField.classList.add("hidden");
            }

            if (opts.docType && docTypeEl) {
                const val = opts.docType;
                if (Array.from(docTypeEl.options).some((o) => o.value === val)) {
                    docTypeEl.value = val;
                }
            }

            closeUploadModal();
            const modal = $("#upload-document-modal");
            if (modal) {
                modal.classList.remove("hidden");
                modal.setAttribute("aria-hidden", "false");
            }
        }

        const uploadModalBackdrop = $("#upload-modal-backdrop");
        if (uploadModalBackdrop) {
            uploadModalBackdrop.addEventListener("click", closeUploadModal);
        }
        const uploadModalCancel = $("#upload-modal-cancel");
        if (uploadModalCancel) {
            uploadModalCancel.addEventListener("click", closeUploadModal);
        }

        const uploadFileInput = $("#upload-file-input");
        const uploadDropzone = $("#upload-dropzone");
        const uploadDropzonePrompt = $("#upload-dropzone-prompt");
        const uploadDropzoneFilename = $("#upload-dropzone-filename");
        const uploadFileError = $("#upload-file-error");
        const uploadBrowseBtn = uploadDropzone && uploadDropzone.querySelector(".upload-browse");

        if (uploadBrowseBtn && uploadFileInput) {
            uploadBrowseBtn.addEventListener("click", (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadFileInput.click();
            });
        }
        if (uploadDropzone && uploadFileInput) {
            uploadDropzone.addEventListener("click", (e) => {
                if (e.target === uploadDropzone || e.target === uploadDropzonePrompt || (e.target && e.target.classList && e.target.classList.contains("upload-browse"))) return;
                if (e.target.closest && e.target.closest(".upload-browse")) return;
                uploadFileInput.click();
            });
            uploadDropzone.addEventListener("dragover", (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadDropzone.classList.add("upload-dropzone-dragover");
            });
            uploadDropzone.addEventListener("dragleave", (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadDropzone.classList.remove("upload-dropzone-dragover");
            });
            uploadDropzone.addEventListener("drop", (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadDropzone.classList.remove("upload-dropzone-dragover");
                const files = e.dataTransfer && e.dataTransfer.files;
                if (files && files.length) uploadFileInput.files = files;
                uploadFileInput.dispatchEvent(new Event("change", { bubbles: true }));
            });
        }
        if (uploadFileInput && uploadFileError) {
            uploadFileInput.addEventListener("change", () => {
                const file = uploadFileInput.files && uploadFileInput.files[0];
                uploadFileError.classList.add("hidden");
                uploadFileError.textContent = "";
                if (uploadDropzonePrompt && uploadDropzoneFilename) {
                    if (file) {
                        uploadDropzonePrompt.classList.add("hidden");
                        uploadDropzoneFilename.textContent = file.name;
                        uploadDropzoneFilename.classList.remove("hidden");
                    } else {
                        uploadDropzonePrompt.classList.remove("hidden");
                        uploadDropzoneFilename.textContent = "";
                        uploadDropzoneFilename.classList.add("hidden");
                    }
                }
                if (!file) return;
                if (!isUploadAllowed(file.name)) {
                    uploadFileError.textContent = "Invalid file type. Allowed: .pdf, .jpg, .jpeg, .png, .tiff";
                    uploadFileError.classList.remove("hidden");
                    return;
                }
                if (file.size > UPLOAD_MAX_BYTES) {
                    uploadFileError.textContent = "File too large. Maximum size is 20MB.";
                    uploadFileError.classList.remove("hidden");
                }
            });
        }

        const uploadForm = $("#upload-document-form");
        if (uploadForm) {
            uploadForm.addEventListener("submit", async (e) => {
                e.preventDefault();
                const propertySelectEl = $("#upload-property-select");
                let propertyId = null;
                if (propertySelectEl && propertySelectEl.value) {
                    propertyId = propertySelectEl.value;
                }
                if (propertyId == null || propertyId === "") {
                    propertyId = window.MORPHIQ_PROPERTY && window.MORPHIQ_PROPERTY.propertyId;
                }
                if (propertyId == null || propertyId === "") {
                    if (uploadFileError) {
                        uploadFileError.textContent = "Please select a property.";
                        uploadFileError.classList.remove("hidden");
                    }
                    return;
                }
                const fileInput = $("#upload-file-input");
                const file = fileInput && fileInput.files && fileInput.files[0];
                if (!file) {
                    if (uploadFileError) {
                        uploadFileError.textContent = "Please select a file.";
                        uploadFileError.classList.remove("hidden");
                    }
                    return;
                }
                if (!isUploadAllowed(file.name)) {
                    if (uploadFileError) {
                        uploadFileError.textContent = "Invalid file type. Allowed: .pdf, .jpg, .jpeg, .png, .tiff";
                        uploadFileError.classList.remove("hidden");
                    }
                    return;
                }
                if (file.size > UPLOAD_MAX_BYTES) {
                    if (uploadFileError) {
                        uploadFileError.textContent = "File too large. Maximum size is 20MB.";
                        uploadFileError.classList.remove("hidden");
                    }
                    return;
                }

                const submitBtn = $("#upload-modal-submit");
                const docTypeEl = $("#upload-doc-type");
                const docType = docTypeEl ? docTypeEl.value : "Other";
                const notesEl = $("#upload-notes");
                const notes = notesEl ? notesEl.value.trim() : "";

                if (uploadFileError) {
                    uploadFileError.textContent = "";
                    uploadFileError.classList.add("hidden");
                }
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.textContent = "Uploading…";
                }

                const formData = new FormData();
                formData.append("file", file);
                formData.append("property_id", String(propertyId));
                formData.append("document_type", docType || "Other");
                if (notes) formData.append("notes", notes);

                try {
                    const res = await fetch("/api/documents/upload", {
                        method: "POST",
                        credentials: "same-origin",
                        body: formData,
                    });
                    const data = await res.json().catch(() => ({}));
                    if (!res.ok) {
                        if (uploadFileError) {
                            uploadFileError.textContent = (data && data.error) || `Upload failed (${res.status})`;
                            uploadFileError.classList.remove("hidden");
                        }
                        return;
                    }
                    closeUploadModal();
                    showUploadToast("Document uploaded — it will appear after processing (1–2 minutes).");
                } catch (err) {
                    if (uploadFileError) {
                        uploadFileError.textContent = err.message || "Upload failed.";
                        uploadFileError.classList.remove("hidden");
                    }
                } finally {
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.textContent = "Upload";
                    }
                }
            });
        }

        document.addEventListener("keydown", (e) => {
            if (e.key !== "Escape") return;
            const modal = $("#upload-document-modal");
            if (modal && !modal.classList.contains("hidden")) {
                closeUploadModal();
                e.stopImmediatePropagation();
            }
        });

        return { openUploadModal, closeUploadModal, showUploadToast };
    }

    function getClientForNotifications() {
        const portal = window.MORPHIQ_PORTAL;
        if (portal && portal.clientName) return portal.clientName;
        const prop = window.MORPHIQ_PROPERTY;
        if (prop && prop.clientName) return prop.clientName;
        const comp = window.MORPHIQ_COMPLIANCE;
        if (comp && comp.clientName) return comp.clientName;
        const params = new URLSearchParams(window.location.search);
        return params.get("client") || "";
    }

    let notificationActions = [];

    function fetchNotifications() {
        const clientName = getClientForNotifications();
        let url = "/api/compliance";
        if (clientName) {
            url += `?client=${encodeURIComponent(clientName)}`;
        }
        // If user has marked notifications as seen this session, keep them hidden
        let hasSeen = false;
        try {
            hasSeen = sessionStorage.getItem("morphiq_notifications_seen") === "1";
        } catch (err) {}

        fetch(url)
            .then((res) => res.json())
            .then((data) => {
                if (!data || !Array.isArray(data.actions)) {
                    notificationActions = [];
                } else {
                    notificationActions = data.actions;
                }
                const count = notificationActions.length;
                const badge = $("#notification-badge");
                if (badge) {
                    if (hasSeen) {
                        badge.style.display = "none";
                    } else {
                        badge.textContent = String(count);
                        badge.style.display = count > 0 ? "" : "none";
                    }
                }
            })
            .catch(() => {
                notificationActions = [];
                const badge = $("#notification-badge");
                if (badge) badge.style.display = "none";
            });
    }

    function getCompliancePageUrl() {
        const clientName = getClientForNotifications();
        if (clientName) {
            return `/compliance?client=${encodeURIComponent(clientName)}`;
        }
        return "/compliance";
    }

    function renderNotificationDropdown() {
        const dropdown = $("#notification-dropdown");
        if (!dropdown) return;
        const count = notificationActions.length;
        const top5 = notificationActions.slice(0, 5);
        const complianceUrl = getCompliancePageUrl();

        if (count === 0) {
            dropdown.innerHTML = `
                <div class="notification-dropdown-header">
                    <span class="notification-dropdown-title">Notifications</span>
                    <span class="notification-dropdown-count">0</span>
                </div>
                <div class="notification-dropdown-body">
                    <div class="notification-dropdown-empty">✓ All clear — no urgent items</div>
                </div>
                <div class="notification-dropdown-footer">
                    <a href="${complianceUrl}" class="notification-dropdown-viewall">View all</a>
                </div>`;
            return;
        }

        const NOTIFICATION_FOCUS_SLUGS = { gas_safety: "gas-safety-certificate", eicr: "eicr", epc: "epc", deposit: "deposit-protection" };
        const clientName = getClientForNotifications();
        const cardsHtml = top5
            .map((a) => {
                let href = a.property_id ? `/property/${a.property_id}` : complianceUrl;
                const typeSlug = NOTIFICATION_FOCUS_SLUGS[(a.type || "").trim()];
                if (a.property_id && typeSlug) {
                    const params = ["focus=" + encodeURIComponent(typeSlug)];
                    if (clientName) params.push("client=" + encodeURIComponent(clientName));
                    href = "/property/" + a.property_id + "?" + params.join("&");
                }
                const status = (a.status || "").trim();
                const dotClass = status === "expired" ? "notification-dot expired" : status === "expiring_soon" ? "notification-dot expiring" : "notification-dot missing";
                const severity = (a.severity || "").trim();
                return `
                    <a class="notification-action-card" href="${href}" data-property-id="${a.property_id || ""}">
                        <span class="${dotClass}"></span>
                        <div class="notification-action-card-inner">
                            <div class="notification-action-main">
                                <span class="notification-action-type">${(a.type_label || "Certificate").replace(/</g, "&lt;")}</span>
                                <span class="notification-action-badge">${(a.badge_text || "").replace(/</g, "&lt;")}</span>
                            </div>
                            <div class="notification-action-address">${(a.property || "—").replace(/</g, "&lt;")}</div>
                            ${severity ? `<div class="notification-action-severity">${severity.replace(/</g, "&lt;")}</div>` : ""}
                        </div>
                    </a>`;
            })
            .join("");

        dropdown.innerHTML = `
            <div class="notification-dropdown-header">
                <span class="notification-dropdown-title">Notifications</span>
                <span class="notification-dropdown-count">${count}</span>
                <button type="button" class="notification-dropdown-mark-seen" id="notification-mark-seen">Mark all as seen</button>
            </div>
            <div class="notification-dropdown-body">
                ${cardsHtml}
            </div>
            <div class="notification-dropdown-footer">
                <a href="${complianceUrl}" class="notification-dropdown-viewall">View all</a>
            </div>`;

        const markSeenBtn = $("#notification-mark-seen");
        if (markSeenBtn) {
            markSeenBtn.addEventListener("click", (e) => {
                e.preventDefault();
                e.stopPropagation();
                try {
                    sessionStorage.setItem("morphiq_notifications_seen", "1");
                } catch (err) {}
                const badge = $("#notification-badge");
                if (badge) badge.style.display = "none";
                closeNotificationDropdown();
            });
        }
    }

    function toggleNotificationDropdown() {
        const dropdown = $("#notification-dropdown");
        if (!dropdown) return;
        const isOpen = !dropdown.classList.contains("hidden");
        if (isOpen) {
            dropdown.classList.add("hidden");
            document.removeEventListener("click", closeNotificationDropdownOnClickOutside);
            document.removeEventListener("keydown", closeNotificationDropdownOnEscape);
        } else {
            renderNotificationDropdown();
            dropdown.classList.remove("hidden");
            setTimeout(() => {
                document.addEventListener("click", closeNotificationDropdownOnClickOutside);
                document.addEventListener("keydown", closeNotificationDropdownOnEscape);
            }, 0);
        }
    }

    function closeNotificationDropdown() {
        const dropdown = $("#notification-dropdown");
        if (dropdown && !dropdown.classList.contains("hidden")) {
            dropdown.classList.add("hidden");
            document.removeEventListener("click", closeNotificationDropdownOnClickOutside);
            document.removeEventListener("keydown", closeNotificationDropdownOnEscape);
        }
    }

    function closeNotificationDropdownOnClickOutside(e) {
        const wrapper = document.querySelector(".notification-bell-wrapper");
        const dropdown = $("#notification-dropdown");
        if (!wrapper || !dropdown || dropdown.classList.contains("hidden")) return;
        if (wrapper.contains(e.target)) return;
        closeNotificationDropdown();
    }

    function closeNotificationDropdownOnEscape(e) {
        if (e.key !== "Escape") return;
        closeNotificationDropdown();
    }

    function initNotificationBell() {
        const bell = $("#notification-bell");
        const dropdown = $("#notification-dropdown");
        if (!bell || !dropdown) return;

        fetchNotifications();

        bell.addEventListener("click", (e) => {
            e.stopPropagation();
            toggleNotificationDropdown();
        });
    }

    function initSignOutConfirmation() {
        $$(".sign-out-link").forEach((link) => {
            link.addEventListener("click", (e) => {
                e.preventDefault();
                if (confirm("Sign out of MorphIQ?")) {
                    window.location.href = "/logout";
                }
            });
        });
    }

    function init() {
        const isDocumentViewPage = !!document.querySelector("#document-view-root");
        const isPropertyPage = !!document.querySelector("#property-detail-root");
        const isCompliancePage = !!document.querySelector("#compliance-root");
        const isAiChatPage = !!document.querySelector("#ai-chat-page-form");
        const portalConfig = window.MORPHIQ_PORTAL || {};
        const isClientPicker = !!document.querySelector("#client-picker-root") && !!portalConfig.showClientPicker;

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
                hypothesisId: 'H1',
                location: 'portal_new/static/portal.js:init',
                message: 'Portal init flags',
                data: {
                    path: window.location.pathname,
                    isDocumentViewPage,
                    isPropertyPage,
                    isCompliancePage,
                    isAiChatPage,
                    isClientPicker,
                },
                timestamp: Date.now(),
            }),
        }).catch(() => {});
        // #endregion agent log

        initSignOutConfirmation();

        const sidebarAiBtn = document.getElementById("sidebar-ai-assistant");
        if (sidebarAiBtn) {
            sidebarAiBtn.addEventListener("click", () => {
                const client = getClientForNotifications();
                const qs = client ? "?client=" + encodeURIComponent(client) : "";
                window.location.href = "/ask-ai" + qs;
            });
        }

        let uploadModalApi = null;
        if (document.querySelector("#upload-document-modal")) {
            uploadModalApi = initUploadModal();
            uploadModalApiRef = uploadModalApi;
        }

        if (document.querySelector("#notification-bell")) {
            initNotificationBell();
        }

        if (document.querySelector(".search-container")) {
            initSearchDropdown();
        }

        initChat();

        if (isAiChatPage) {
            initAiChatPage();
        } else if (isDocumentViewPage) {
            initDocumentViewerPage();
        } else if (isPropertyPage) {
            initPropertyPage(uploadModalApi);
        } else if (isCompliancePage) {
            initCompliancePage(uploadModalApi);
        } else if (isClientPicker) {
            fetchClientsForPicker();
        } else if (document.querySelector("[data-page='overview']")) {
            // Standalone /overview layout: data + UI driven by overview.html (no archive workspace).
        } else if (document.querySelector("[data-page='properties']")) {
            // Standalone /properties split-panel: properties.js + no archive workspace.
        } else if (document.querySelector("[data-page='documents']")) {
            // Standalone /documents library: documents.js + no archive workspace.
        } else if (document.querySelector("[data-page='packs']")) {
            // Standalone /packs layout (placeholder packs UI).
        } else if (document.querySelector("[data-page='reports']")) {
            // Standalone /reports + audit trail fetch.
        } else if (document.querySelector("[data-page='settings']")) {
            // Standalone /settings (inline scripts).
        } else {
            initArchivePage();
            initDashboardOverview(uploadModalApi);

            // Tabs + sidebar links
            (function initDashboardTabs() {
                const tabs = $$(".dashboard-tab");
                const overviewView = $("#dashboard-overview");
                const archiveView = $("#dashboard-archive");
                if (!tabs.length || !overviewView || !archiveView) return;

                const sidebarLinks = $$(".portal-sidebar-nav .portal-sidebar-link");
                const overviewLink = Array.from(sidebarLinks).find((link) =>
                    ((link.textContent || "").trim().toLowerCase().includes("overview"))
                );
                const propertiesLink = Array.from(sidebarLinks).find((link) =>
                    ((link.textContent || "").trim().toLowerCase().includes("properties"))
                );

                function setSidebarActive(view) {
                    if (overviewLink) {
                        overviewLink.classList.toggle("active", view === "overview");
                    }
                    if (propertiesLink) {
                        propertiesLink.classList.toggle("active", view === "archive");
                    }
                }

                function setView(view) {
                    tabs.forEach((t) => t.classList.toggle("active", t.getAttribute("data-view") === view));
                    if (view === "archive") {
                        overviewView.style.display = "none";
                        archiveView.style.display = "";
                    } else {
                        overviewView.style.display = "";
                        archiveView.style.display = "none";
                    }
                    if (view === "archive") {
                        window.location.hash = "#properties";
                    } else {
                        window.location.hash = "#overview";
                    }
                    setSidebarActive(view);
                }

                tabs.forEach((tab) => {
                    tab.addEventListener("click", () => {
                        const v = tab.getAttribute("data-view") || "overview";
                        setView(v);
                    });
                });

                const hash = window.location.hash || "";
                const path = (window.location.pathname || "").replace(/\/+$/, "") || "/";
                const isArchivePath =
                    path.endsWith("/archive") || path.endsWith("/properties");
                const isOverviewPath =
                    path.endsWith("/overview") ||
                    path.endsWith("/dashboard") ||
                    path === "/" ||
                    path === "";
                let initial = "overview";
                if (isArchivePath) initial = "archive";
                else if (isOverviewPath) initial = hash === "#properties" || hash === "#archive" ? "archive" : "overview";
                else if (hash === "#archive" || hash === "#properties") initial = "archive";
                setView(initial);
            })();
        }
    }

    // Run on DOM ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();

// ── Add-to-Pack modal (global — available on every page that loads portal.js) ─
(function () {
    "use strict";

    var _currentDocId = null;
    var _toastTimer   = null;

    function _withClient(url) {
        var cp = new URLSearchParams(window.location.search).get("client")
            || (window.MORPHIQ_PORTAL && window.MORPHIQ_PORTAL.clientName) || "";
        if (!String(cp).trim()) return url;
        return url + (url.includes("?") ? "&" : "?") + "client=" + encodeURIComponent(String(cp).trim());
    }

    function _esc(s) {
        return String(s == null ? "" : s)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    function _backdrop() { return document.getElementById("atp-backdrop"); }
    function _toastEl()  { return document.getElementById("atp-toast"); }

    function _open(documentId) {
        _currentDocId = parseInt(documentId, 10);
        if (!Number.isFinite(_currentDocId)) return;
        var bd = _backdrop();
        if (!bd) return;
        bd.hidden = false;
        bd.focus();
        _loadPacks();
    }

    function _close() {
        var bd = _backdrop();
        if (bd) bd.hidden = true;
        _currentDocId = null;
    }

    function _showToast(msg, isError) {
        var t = _toastEl();
        if (!t) return;
        t.textContent = msg;
        t.className = "atp-toast " + (isError ? "atp-toast--error" : "atp-toast--ok");
        t.hidden = false;
        clearTimeout(_toastTimer);
        _toastTimer = setTimeout(function () { if (t) t.hidden = true; }, 3000);
    }

    async function _loadPacks() {
        var body = document.getElementById("atp-body");
        if (!body) return;
        body.innerHTML = '<div class="atp-loading">Loading packs\u2026</div>';
        try {
            var res  = await fetch(_withClient("/api/packs"), { credentials: "same-origin" });
            var data = await res.json().catch(function () { return {}; });
            _renderPacks(data.packs || []);
        } catch (e) {
            body.innerHTML = '<div class="atp-error">Failed to load packs.</div>';
            console.error("[atp] loadPacks:", e);
        }
    }

    function _renderPacks(packs) {
        var body = document.getElementById("atp-body");
        if (!body) return;
        if (!packs.length) {
            body.innerHTML = '<p class="atp-empty">No packs yet \u2014 use \u201cNew pack \u0026 add\u201d below.</p>';
            return;
        }
        body.innerHTML = packs.map(function (pk) {
            return '<button type="button" class="atp-pack-btn"'
                + ' data-pack-id="' + pk.id + '"'
                + ' data-pack-name="' + _esc(pk.name) + '">'
                + '<span class="atp-pack-name">' + _esc(pk.name) + '</span>'
                + '<span class="atp-pack-count">' + (pk.doc_count || 0) + ' docs</span>'
                + '</button>';
        }).join("");
        body.querySelectorAll(".atp-pack-btn").forEach(function (btn) {
            btn.addEventListener("click", function () {
                _addToExistingPack(
                    parseInt(btn.getAttribute("data-pack-id"), 10),
                    btn.getAttribute("data-pack-name") || "pack"
                );
            });
        });
    }

    async function _addToExistingPack(packId, packName) {
        if (!_currentDocId) return;
        var docId = _currentDocId;
        _close();
        try {
            var res = await fetch(_withClient("/api/packs/" + packId + "/documents"), {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ document_ids: [docId] }),
            });
            if (!res.ok) {
                var d = await res.json().catch(function () { return {}; });
                throw new Error(d.error || ("HTTP " + res.status));
            }
            _showToast("Added to \u201c" + packName + "\u201d");
        } catch (e) {
            _showToast("Could not add to pack", true);
            console.error("[atp] addToExistingPack:", e);
        }
    }

    async function _createAndAdd() {
        var name = window.prompt("New pack name:");
        if (!name || !name.trim()) return;
        var docId = _currentDocId;
        _close();
        try {
            var r1 = await fetch(_withClient("/api/packs"), {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: name.trim() }),
            });
            var d1 = await r1.json().catch(function () { return {}; });
            if (!r1.ok) throw new Error(d1.error || ("HTTP " + r1.status));
            var packId = d1.pack && d1.pack.id;
            if (packId && docId) {
                var r2 = await fetch(_withClient("/api/packs/" + packId + "/documents"), {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ document_ids: [docId] }),
                });
                if (!r2.ok) throw new Error("HTTP " + r2.status);
            }
            _showToast("Added to new pack \u201c" + name.trim() + "\u201d");
        } catch (e) {
            _showToast("Could not create pack", true);
            console.error("[atp] createAndAdd:", e);
        }
    }

    function _bind() {
        var bd = _backdrop();
        if (bd) {
            bd.addEventListener("click", function (e) {
                if (e.target === bd) _close();
            });
        }
        var closeBtn = document.getElementById("atp-close");
        if (closeBtn) closeBtn.addEventListener("click", _close);
        var newBtn = document.getElementById("atp-new-pack-btn");
        if (newBtn) newBtn.addEventListener("click", _createAndAdd);
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") {
                var b = _backdrop();
                if (b && !b.hidden) _close();
            }
        });
        // Global delegation: any .atp-trigger[data-document-id] opens the modal
        document.addEventListener("click", function (e) {
            var btn = e.target.closest(".atp-trigger[data-document-id]");
            if (!btn) return;
            e.preventDefault();
            _open(btn.getAttribute("data-document-id"));
        });
    }

    function _init() {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", _bind);
        } else {
            _bind();
        }
    }

    // Expose for programmatic use from page-level scripts
    window.AtpModal = { open: _open, close: _close };
    _init();
})();
