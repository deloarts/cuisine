/**
 * A browser smoke check of the real app: it signs in as the demo accounts of
 * `make seed-dev`, visits every main page on a desktop and a phone screen,
 * and records console errors, failed API calls and a screenshot of each page.
 * It runs against the running dev stack (`make infra`, the backend on :3000,
 * Vite on :5173) inside the pinned Playwright image (`npm run test:e2e`), on
 * demand and not in CI.
 */
import { defineConfig, devices } from '@playwright/test'

const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:5173'

export default defineConfig({
  testDir: './e2e/smoke',
  fullyParallel: false,
  workers: 1,
  forbidOnly: true,
  timeout: 300_000,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  outputDir: 'test-results',
  use: {
    baseURL: BASE_URL,
    locale: 'en-GB',
    timezoneId: 'Europe/Vienna',
    colorScheme: 'light',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    { name: 'phone', use: { ...devices['Pixel 7'] } },
  ],
})
