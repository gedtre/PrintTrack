import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  retries: 0,
  timeout: 60000,
  use: {
    baseURL: process.env.PRINTTRACK_E2E_URL ?? "http://127.0.0.1:8080",
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
      ? {
          executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,
          args: ["--no-sandbox"],
        }
      : undefined,
    screenshot: "only-on-failure",
    trace: "off",
  },
});
