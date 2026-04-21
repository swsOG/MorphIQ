const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..", "..", "..");
const templatesRoot = path.join(repoRoot, "templates");

function readTemplate(name) {
  return fs.readFileSync(path.join(templatesRoot, name), "utf8");
}

function runTest(name, fn) {
  try {
    fn();
    console.log(`PASS ${name}`);
  } catch (error) {
    console.error(`FAIL ${name}`);
    throw error;
  }
}

runTest("documents page opts into shared explorer toolbar and results shell", () => {
  const template = readTemplate("documents.html");
  assert.match(template, /portal-workspace-shell/);
  assert.match(template, /portal-toolbar-search/);
  assert.match(template, /portal-results-shell/);
});

runTest("packs page uses shared workspace surfaces and modal classes", () => {
  const template = readTemplate("packs.html");
  assert.match(template, /portal-workspace-shell/);
  assert.match(template, /portal-surface-card/);
  assert.match(template, /portal-modal-card/);
});

runTest("reports page adopts shared workspace surfaces and compact action rows", () => {
  const template = readTemplate("reports.html");
  assert.match(template, /portal-workspace-shell/);
  assert.match(template, /portal-surface-card/);
  assert.match(template, /portal-row-actions/);
});

runTest("overview page adopts shared summary chips and navigation cards", () => {
  const template = readTemplate("overview.html");
  assert.match(template, /portal-summary-strip/);
  assert.match(template, /portal-nav-card/);
});

runTest("settings page uses shared pills and surface cards for admin sections", () => {
  const template = readTemplate("settings.html");
  assert.match(template, /portal-workspace-shell/);
  assert.match(template, /portal-surface-card/);
  assert.match(template, /portal-pill/);
});
