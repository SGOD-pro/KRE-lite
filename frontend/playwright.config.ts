import { defineConfig, devices } from '@playwright/test';

/**
 * playwright.config.ts
 *
 * Two project groups:
 *   1. "local" (default) — runs against http://localhost:5173 with a dev server.
 *      All existing E2E specs (citation-flow, session-restrictions, phase-e).
 *
 *   2. "smoke-deployed" — runs smoke-deployed.spec.ts ONLY, no web server needed.
 *      Activated when DEPLOYED_BACKEND_URL env var is set (CI post-deploy).
 *      baseURL is irrelevant (tests navigate to about:blank and use fetch()).
 */

const isSmoke = !!process.env.DEPLOYED_BACKEND_URL;

export default defineConfig({
  testDir: './tests/e2e',
  // Generous global timeout for Bedrock Titan indexing
  timeout: 300_000,
  expect: {
    timeout: 60_000,
  },
  // Run sequentially — parallel would trigger Bedrock rate limits
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    navigationTimeout: 30_000,
    actionTimeout: 30_000,
  },

  projects: [
    {
      // Full E2E suite — requires local dev server (normal mode)
      // Smoke-only mode — no dev server, only smoke-deployed.spec.ts
      name: 'chromium',
      // In normal mode: exclude the deployed smoke spec (needs DEPLOYED_BACKEND_URL)
      // In smoke mode: exclude all non-smoke specs (they need localhost dev server)
      testIgnore: isSmoke
        ? ['**/citation-flow.spec.ts', '**/session-restrictions.spec.ts', '**/phase-e.spec.ts']
        : ['**/smoke-deployed.spec.ts'],
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Only start the dev server when NOT running the deployed smoke tests
  webServer: isSmoke
    ? undefined
    : {
        command: 'npm run dev',
        url: 'http://localhost:5173',
        reuseExistingServer: !process.env.CI,
        timeout: 60_000,
      },
});
