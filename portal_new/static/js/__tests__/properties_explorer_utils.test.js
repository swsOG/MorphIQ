const assert = require("node:assert/strict");

const {
  extractArea,
  calculateComplianceScore,
  buildPropertySearchBlob,
  buildPreviewSummaryItems,
  buildNextActions,
  filterProperties,
  sortProperties,
} = require("../properties_explorer_utils.js");

const sampleProperties = [
  {
    property_id: 1,
    property_address: "303 Fixture Road, Sampletown, ZX3 3CC",
    client_name: "Sample Agency Alpha",
    tenant_name: "Sandra Obi",
    overall_status: "non_compliant",
    latest_activity_date: "2026-04-18T10:00:00Z",
    search_meta: {
      area: "Sampletown",
      document_types: ["EICR", "Gas Safety Certificate", "EPC"],
      document_ids: ["DOC-00031"],
    },
    compliance: {
      gas_safety: { status: "expired" },
      eicr: { status: "expired" },
      epc: { status: "expired" },
      deposit: { status: "missing" },
    },
  },
  {
    property_id: 2,
    property_address: "606 Example Way, Demochester, ZX6 6FF",
    client_name: "Sample Agency Alpha",
    tenant_name: "George Kowalski",
    overall_status: "compliant",
    latest_activity_date: "2026-04-19T12:00:00Z",
    search_meta: {
      area: "Demochester",
      document_types: ["EICR", "Gas Safety Certificate", "EPC", "Deposit Protection Certificate"],
      document_ids: ["DOC-00099"],
    },
    compliance: {
      gas_safety: { status: "valid" },
      eicr: { status: "valid" },
      epc: { status: "valid" },
      deposit: { status: "valid" },
    },
  },
  {
    property_id: 3,
    property_address: "404 Placeholder Drive, Mockford, ZX4 4DD",
    client_name: "Sample Agency Alpha",
    tenant_name: "Priya Nair",
    overall_status: "at_risk",
    latest_activity_date: "2026-04-16T09:30:00Z",
    search_meta: {
      area: "Mockford",
      document_types: ["EICR", "Gas Safety Certificate"],
      document_ids: ["DOC-00420"],
    },
    compliance: {
      gas_safety: { status: "expiring" },
      eicr: { status: "valid" },
      epc: { status: "valid" },
      deposit: { status: "missing" },
    },
  },
];

function runTest(name, fn) {
  try {
    fn();
    console.log(`PASS ${name}`);
  } catch (error) {
    console.error(`FAIL ${name}`);
    throw error;
  }
}

runTest("extractArea returns the middle address segment before the postcode", () => {
  assert.equal(extractArea("303 Fixture Road, Sampletown, ZX3 3CC"), "Sampletown");
  assert.equal(extractArea("404 Placeholder Drive, Mockford, ZX4 4DD"), "Mockford");
});

runTest("calculateComplianceScore ranks compliant properties above non-compliant ones", () => {
  assert.ok(calculateComplianceScore(sampleProperties[1]) > calculateComplianceScore(sampleProperties[2]));
  assert.ok(calculateComplianceScore(sampleProperties[2]) > calculateComplianceScore(sampleProperties[0]));
});

runTest("buildPropertySearchBlob includes document types, ids, area, and status keywords", () => {
  const blob = buildPropertySearchBlob(sampleProperties[0]);
  assert.match(blob, /sampletown/i);
  assert.match(blob, /eicr/i);
  assert.match(blob, /doc-00031/i);
  assert.match(blob, /expired/i);
  assert.match(blob, /missing/i);
});

runTest("filterProperties matches unified search text across property and document metadata", () => {
  assert.deepEqual(
    filterProperties(sampleProperties, { query: "doc-00099" }).map((row) => row.property_id),
    [2]
  );
  assert.deepEqual(
    filterProperties(sampleProperties, { query: "gas safety" }).map((row) => row.property_id),
    [1, 2, 3]
  );
  assert.deepEqual(
    filterProperties(sampleProperties, { query: "sampletown", area: "Sampletown" }).map((row) => row.property_id),
    [1]
  );
});

runTest("sortProperties orders rows by compliance and latest activity", () => {
  assert.deepEqual(
    sortProperties(sampleProperties, "most_compliant").map((row) => row.property_id),
    [2, 3, 1]
  );
  assert.deepEqual(
    sortProperties(sampleProperties, "least_compliant").map((row) => row.property_id),
    [1, 3, 2]
  );
  assert.deepEqual(
    sortProperties(sampleProperties, "last_updated").map((row) => row.property_id),
    [2, 1, 3]
  );
});

runTest("buildPreviewSummaryItems returns compact stats for the preview header", () => {
  const items = buildPreviewSummaryItems({
    documents: [{}, {}, {}, {}],
    compliance: sampleProperties[0].compliance,
    latest_activity_date: "2026-04-18T10:00:00Z",
  });
  assert.deepEqual(items, [
    { label: "Documents", value: "4" },
    { label: "Missing", value: "1" },
    { label: "Updated", value: "2026-04-18T10:00:00Z" },
  ]);
});

runTest("buildNextActions prioritizes urgent certificate work and caps the list", () => {
  const actions = buildNextActions({
    gas_safety: { status: "expired" },
    eicr: { status: "expired" },
    epc: { status: "missing" },
    deposit: { status: "expiring" },
  });
  assert.deepEqual(actions, [
    "Upload a renewed Gas Safety certificate.",
    "Upload a renewed EICR certificate.",
    "Add the missing EPC document.",
  ]);
});
