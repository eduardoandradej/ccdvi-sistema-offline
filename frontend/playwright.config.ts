import { defineConfig } from "@playwright/test";

// Pré-requisito: API + frontend em execução (ver README) e banco com seed --demo-records.
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.DVI_E2E_BASE_URL ?? "http://127.0.0.1:4173",
    screenshot: "only-on-failure",
    launchOptions: process.env.DVI_CHROMIUM ? { executablePath: process.env.DVI_CHROMIUM } : {},
  },
});
