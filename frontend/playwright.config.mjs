import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 20_000,
  expect: { timeout: 7000 },
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:8082",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width:1440,height:900 } } },
    { name: "tablet", use: { ...devices["Desktop Chrome"], viewport: { width:768,height:1024 } } },
    { name: "mobile", use: { ...devices["Desktop Chrome"], viewport: { width:390,height:844 }, isMobile:true,hasTouch:true } },
  ],
  webServer: {
    command: "python3 -m http.server 8082 --bind 127.0.0.1",
    url: "http://127.0.0.1:8082/",
    reuseExistingServer: !process.env.CI,
    timeout: 15000,
  },
});
