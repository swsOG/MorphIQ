const { defineConfig } = require("@playwright/test");

const smokePython = process.env.MORPHIQ_SMOKE_PYTHON || "python";
const smokePort = process.env.MORPHIQ_SMOKE_PORT || "5015";

module.exports = defineConfig({
  testDir: "./tests/smoke",
  timeout: 45_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: `http://127.0.0.1:${smokePort}`,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: `${smokePython} scripts/start_portal_smoke_server.py`,
    url: `http://127.0.0.1:${smokePort}/login`,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      ...process.env,
      MORPHIQ_SMOKE_PORT: smokePort,
    },
  },
});
