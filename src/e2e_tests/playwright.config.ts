import { defineConfig } from "@playwright/test";

// E2E tests use non-default ports to avoid conflicts with a dev server
const BACKEND_PORT = process.env.BARK_E2E_PORT || "18997";
const BASE_URL =
  process.env.BARK_TEST_URL || `http://localhost:${BACKEND_PORT}`;
const BROWSERS = process.env.PLAYWRIGHT_BROWSERS_PATH || "";

export default defineConfig({
  testDir: "./e2e",
  timeout: 300_000,
  retries: 0,
  workers: process.env.BARK_E2E_WORKERS || "100%",
  fullyParallel: true,
  globalSetup: "./global-setup.ts",
  globalTeardown: "./global-teardown.ts",
  use: {
    baseURL: BASE_URL,
    headless: true,
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        launchOptions: {
          executablePath:
            process.env.CHROME_PATH ||
            `${BROWSERS}/chromium-1217/chrome-linux64/chrome`,
          args: ["--enable-unsafe-swiftshader"],
        },
      },
    },
    {
      name: "firefox",
      use: {
        browserName: "firefox",
        launchOptions: {
          executablePath: `${BROWSERS}/firefox-1511/firefox/firefox`,
        },
      },
    },
    {
      name: "webkit",
      use: {
        browserName: "webkit",
      },
    },
  ],
});
