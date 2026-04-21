(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.PropertiesExplorerUtils = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const CERT_KEYS = ["gas_safety", "eicr", "epc", "deposit"];
  const CERT_LABELS = {
    gas_safety: "Gas Safety",
    eicr: "EICR",
    epc: "EPC",
    deposit: "Deposit",
  };
  const STATUS_SCORE = {
    valid: 100,
    no_expiry: 100,
    expiring: 70,
    expiring_soon: 70,
    expired: 25,
    missing: 0,
  };

  function normalizeText(value) {
    return String(value == null ? "" : value).trim().toLowerCase();
  }

  function extractPostcode(address) {
    const match = String(address || "").match(/[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}/i);
    return match ? match[0].toUpperCase() : "";
  }

  function extractArea(address) {
    const parts = String(address || "")
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean);
    if (parts.length >= 3 && extractPostcode(parts[parts.length - 1])) {
      return parts[parts.length - 2];
    }
    if (parts.length >= 2 && !extractPostcode(parts[parts.length - 1])) {
      return parts[parts.length - 1];
    }
    return "";
  }

  function complianceStatuses(property) {
    const compliance = property && property.compliance ? property.compliance : {};
    return CERT_KEYS.map((key) => {
      const entry = compliance[key] || {};
      return normalizeText(entry.status || property[key] || "missing") || "missing";
    });
  }

  function calculateComplianceScore(property) {
    const statuses = complianceStatuses(property);
    if (!statuses.length) return 0;
    const total = statuses.reduce((sum, status) => sum + (STATUS_SCORE[status] ?? 0), 0);
    return Math.round(total / statuses.length);
  }

  function countMissingDocuments(property) {
    return complianceStatuses(property).filter((status) => status === "missing").length;
  }

  function countAttentionDocuments(property) {
    return complianceStatuses(property).filter((status) => status === "missing" || status === "expired").length;
  }

  function complianceMap(detail) {
    if (!detail) return {};
    if (detail.compliance) return detail.compliance;
    return {
      gas_safety: detail.gas_safety || {},
      eicr: detail.eicr || {},
      epc: detail.epc || {},
      deposit: detail.deposit || {},
    };
  }

  function buildPropertySearchBlob(property) {
    const meta = property && property.search_meta ? property.search_meta : {};
    const statusTerms = complianceStatuses(property);
    const keywords = [];
    if (statusTerms.includes("expired")) keywords.push("expired");
    if (statusTerms.includes("missing")) keywords.push("missing");
    if (statusTerms.includes("expiring") || statusTerms.includes("expiring_soon")) keywords.push("expiring");
    if ((property && property.overall_status) === "non_compliant") keywords.push("urgent", "non compliant");
    if ((property && property.overall_status) === "at_risk") keywords.push("at risk");
    if ((property && property.overall_status) === "compliant") keywords.push("compliant");

    return [
      property && property.property_address,
      property && property.client_name,
      property && property.tenant_name,
      property && property.area,
      property && property.borough,
      meta.area,
      Array.isArray(meta.document_types) ? meta.document_types.join(" ") : "",
      Array.isArray(meta.document_ids) ? meta.document_ids.join(" ") : "",
      statusTerms.join(" "),
      keywords.join(" "),
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
  }

  function buildPreviewSummaryItems(detail) {
    return [
      { label: "Documents", value: String(((detail && detail.documents) || []).length) },
      { label: "Missing", value: String(countMissingDocuments(detail || {})) },
      { label: "Updated", value: detail && detail.latest_activity_date ? String(detail.latest_activity_date) : "" },
    ];
  }

  function buildNextActions(detail, limit) {
    const maxItems = Number.isFinite(limit) ? limit : 3;
    const compliance = complianceMap(detail);
    const expired = [];
    const missing = [];
    const expiring = [];

    CERT_KEYS.forEach((key) => {
      const status = normalizeText((compliance[key] || {}).status || "missing");
      const label = CERT_LABELS[key] || key;
      if (status === "expired") {
        expired.push(`Upload a renewed ${label} certificate.`);
      } else if (status === "missing") {
        missing.push(`Add the missing ${label} document.`);
      } else if (status === "expiring" || status === "expiring_soon") {
        expiring.push(`Plan the next ${label} renewal before it expires.`);
      }
    });

    const items = expired.concat(missing, expiring);
    if (!items.length) {
      return ["Everything essential is on file. Use the search box to open supporting documents quickly."];
    }
    return items.slice(0, maxItems);
  }

  function filterProperties(properties, options) {
    const settings = Object.assign(
      {
        query: "",
        area: "all",
        risk: "all",
        missing: "all",
      },
      options || {}
    );
    const query = normalizeText(settings.query);
    const area = normalizeText(settings.area);
    const risk = normalizeText(settings.risk);
    const missing = normalizeText(settings.missing);

    return (properties || []).filter((property) => {
      const propertyArea = normalizeText(property.area || property.borough || (property.search_meta || {}).area || extractArea(property.property_address));
      if (area && area !== "all" && propertyArea !== area) return false;

      const overallStatus = normalizeText(property.overall_status);
      if (risk && risk !== "all" && overallStatus !== risk) return false;

      if (missing === "missing_only" && countMissingDocuments(property) < 1) return false;
      if (missing === "attention_only" && countAttentionDocuments(property) < 1) return false;

      if (!query) return true;
      return buildPropertySearchBlob(property).includes(query);
    });
  }

  function compareText(a, b) {
    return String(a || "").localeCompare(String(b || ""), undefined, { sensitivity: "base" });
  }

  function compareDatesDesc(a, b) {
    return String(b || "").localeCompare(String(a || ""));
  }

  function sortProperties(properties, sortKey) {
    const list = (properties || []).slice();
    const key = normalizeText(sortKey || "most_compliant");
    const compareByScore = (left, right, direction) => {
      const scoreDelta = calculateComplianceScore(right) - calculateComplianceScore(left);
      if (direction === "asc") {
        if (scoreDelta !== 0) return -scoreDelta;
      } else if (scoreDelta !== 0) {
        return scoreDelta;
      }
      return compareText(left.property_address, right.property_address);
    };

    if (key === "least_compliant") {
      return list.sort((left, right) => compareByScore(left, right, "asc"));
    }
    if (key === "last_updated") {
      return list.sort((left, right) => {
        const dateDelta = compareDatesDesc(left.latest_activity_date, right.latest_activity_date);
        if (dateDelta !== 0) return dateDelta;
        return compareText(left.property_address, right.property_address);
      });
    }
    if (key === "borough") {
      return list.sort((left, right) => {
        const areaDelta = compareText(
          left.area || left.borough || extractArea(left.property_address),
          right.area || right.borough || extractArea(right.property_address)
        );
        if (areaDelta !== 0) return areaDelta;
        return compareText(left.property_address, right.property_address);
      });
    }
    return list.sort((left, right) => compareByScore(left, right, "desc"));
  }

  function groupPropertiesByArea(properties) {
    const groups = new Map();
    (properties || []).forEach((property) => {
      const key = property.area || property.borough || (property.search_meta || {}).area || extractArea(property.property_address) || "Unsorted";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(property);
    });
    return Array.from(groups.entries()).map(([area, items]) => ({ area, items }));
  }

  return {
    extractPostcode,
    extractArea,
    calculateComplianceScore,
    countMissingDocuments,
    countAttentionDocuments,
    buildPreviewSummaryItems,
    buildNextActions,
    buildPropertySearchBlob,
    filterProperties,
    sortProperties,
    groupPropertiesByArea,
  };
});
