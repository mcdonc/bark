import { defineConfig } from "@playwright/test";

// E2E tests use non-default ports to avoid conflicts with a dev server
const BACKEND_PORT = process.env.BARK_E2E_PORT || "18997";
const BASE_URL =
  process.env.BARK_TEST_URL || `http://localhost:${BACKEND_PORT}`;
const BROWSERS = process.env.PLAYWRIGHT_BROWSERS_PATH || "";

const chromiumUse = {
  launchOptions: {
    executablePath:
      process.env.CHROME_PATH ||
      `${BROWSERS}/chromium-1217/chrome-linux64/chrome`,
    args: ["--enable-unsafe-swiftshader"],
  },
};

const firefoxUse = {
  browserName: "firefox" as const,
  launchOptions: {
    executablePath: `${BROWSERS}/firefox-1511/firefox/firefox`,
  },
};

const webkitUse = {
  browserName: "webkit" as const,
};

// Browsers run sequentially (chromium → firefox → webkit) to avoid
// overwhelming SQLite with concurrent writes from 60+ parallel tests.
// LLM and non-LLM tests run in separate dependency chains so a flaky
// LLM test doesn't block the non-LLM suite.

export default defineConfig({
  testDir: "./e2e",
  timeout: 300_000,
  retries: 0,
  workers: process.env.BARK_E2E_WORKERS
    ? /^\d+$/.test(process.env.BARK_E2E_WORKERS)
      ? parseInt(process.env.BARK_E2E_WORKERS, 10)
      : process.env.BARK_E2E_WORKERS
    : 4,
  fullyParallel: true,
  globalSetup: "./global-setup.ts",
  globalTeardown: "./global-teardown.ts",
  use: {
    baseURL: BASE_URL,
    headless: true,
    screenshot: "only-on-failure",
  },
  projects: [
    // LLM chain: sequential within each browser, no fail-fast so one
    // flaky test doesn't skip the rest (fullyParallel: false).
    {
      name: "chromium-llm",
      testMatch: "bark-llm.spec.ts",
      fullyParallel: false,
      use: chromiumUse,
    },
    {
      name: "firefox-llm",
      testMatch: "bark-llm.spec.ts",
      dependencies: ["chromium-llm"],
      fullyParallel: false,
      use: firefoxUse,
    },
    {
      name: "webkit-llm",
      testMatch: "bark-llm.spec.ts",
      dependencies: ["firefox-llm"],
      fullyParallel: false,
      use: webkitUse,
    },
    // Non-LLM chain: independent of LLM chain so LLM failures don't
    // block these tests. May overlap with LLM tests.
    {
      name: "chromium",
      testMatch: "bark.spec.ts",
      use: chromiumUse,
    },
    {
      name: "firefox",
      testMatch: "bark.spec.ts",
      dependencies: ["chromium"],
      use: firefoxUse,
    },
    {
      name: "webkit",
      testMatch: "bark.spec.ts",
      dependencies: ["firefox"],
      use: webkitUse,
    },
  ],
});
