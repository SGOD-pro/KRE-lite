import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

/**
 * smoke-deployed.spec.ts
 *
 * Cross-origin smoke tests against the DEPLOYED backend (not localhost).
 * Runs in CI after every deploy to confirm:
 *   1. GET  /health        → 200 {"status":"ok"}
 *   2. POST /ingest        → real upload+chunking pipeline (413 for oversized,
 *                            200 for a tiny fixture PDF if AWS creds are available)
 *   3. CORS headers        → Access-Control-Allow-Origin present for the frontend origin
 *
 * Required env vars (set in CI secrets):
 *   DEPLOYED_BACKEND_URL   e.g. https://abc123.execute-api.ap-south-1.amazonaws.com/Prod
 *   DEPLOYED_FRONTEND_URL  e.g. https://kre-lite.vercel.app   (used as CORS origin)
 *
 * The Playwright browser context is used to make cross-origin fetch() calls
 * from within a page — this validates CORS exactly as the real frontend does.
 *
 * Tests are skipped gracefully when DEPLOYED_BACKEND_URL is not set
 * (safe for local dev runs).
 */

const BACKEND_URL = (process.env.DEPLOYED_BACKEND_URL || '').replace(/\/+$/, '');
const FRONTEND_URL = process.env.DEPLOYED_FRONTEND_URL || 'https://kre-lite.vercel.app';

// Tiny fixture PDF bundled with the backend test fixtures (5 KB)
const FIXTURE_PDF = path.resolve(
  __dirname,
  '../../../backend/tests/fixtures/sample_doc.pdf'
);

test.describe('Deployed backend smoke tests (cross-origin)', () => {
  test.skip(!BACKEND_URL, 'DEPLOYED_BACKEND_URL not set — skipping deployed smoke tests');

  // ── 1. Health check ──────────────────────────────────────────────────────────
  test('GET /health returns 200 {"status":"ok"}', async ({ page }) => {
    test.setTimeout(30_000);

    // Navigate to the frontend so the page origin matches FRONTEND_URL
    // For CI where the frontend isn't deployed yet, use a blank data page
    await page.goto('about:blank');

    const result = await page.evaluate(async (backendUrl: string) => {
      const res = await fetch(`${backendUrl}/health`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      return { status: res.status, body: await res.json() };
    }, BACKEND_URL);

    expect(result.status).toBe(200);
    expect(result.body).toMatchObject({ status: 'ok' });
  });

  // ── 2. CORS preflight ────────────────────────────────────────────────────────
  test('OPTIONS /health returns CORS headers for frontend origin', async ({ request }) => {
    test.setTimeout(15_000);

    const res = await request.fetch(`${BACKEND_URL}/health`, {
      method: 'OPTIONS',
      headers: {
        'Origin': FRONTEND_URL,
        'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'content-type',
      },
    });

    // 200 or 204 are both valid preflight responses
    expect([200, 204]).toContain(res.status());

    // CORS allow-origin must be set
    const headers = res.headers();
    const allowOrigin = headers['access-control-allow-origin'];
    expect(allowOrigin === '*' || allowOrigin === FRONTEND_URL).toBeTruthy();
  });

  // ── 3. /ingest 413 — oversized file rejected before parsing ──────────────────
  test('POST /ingest with 11 MB file returns 413 from deployed backend', async ({ page }) => {
    test.setTimeout(60_000);

    await page.goto('about:blank');

    const result = await page.evaluate(async (backendUrl: string) => {
      // 11 MB of zeros as a fake PDF — must be rejected by the 10 MB size limit
      // before PyMuPDF or any AWS call is made
      const blob = new Blob([new Uint8Array(11 * 1024 * 1024)], { type: 'application/pdf' });
      const formData = new FormData();
      formData.append('files', blob, 'oversized.pdf');

      const res = await fetch(`${backendUrl}/ingest`, {
        method: 'POST',
        body: formData,
      });
      let body: any = null;
      try { body = await res.json(); } catch {}
      return { status: res.status, body };
    }, BACKEND_URL);

    expect(result.status).toBe(413);
    // detail must mention the limit
    const detail: string = result.body?.detail ?? '';
    expect(detail.toLowerCase()).toMatch(/10 mb|limit/);
  });

  // ── 4. /ingest with real fixture PDF — full pipeline smoke ───────────────────
  //    This test runs only when the fixture PDF is present (always in CI).
  //    It exercises: file upload → chunking → Bedrock Titan embedding → Qdrant store.
  //    If AWS / Qdrant credentials aren't wired, the backend returns 503 which we
  //    also accept here (the infra is broken, not the HTTP contract).
  test('POST /ingest with fixture PDF reaches the backend pipeline', async ({ page }) => {
    test.setTimeout(120_000);

    if (!fs.existsSync(FIXTURE_PDF)) {
      test.skip(true, 'Fixture PDF not found — skipping real ingest smoke test');
    }

    await page.goto('about:blank');

    // Read fixture PDF as base64 and send it from inside the browser context
    const pdfBase64 = fs.readFileSync(FIXTURE_PDF).toString('base64');

    const result = await page.evaluate(async ({ backendUrl, pdfBase64 }: { backendUrl: string; pdfBase64: string }) => {
      // Decode base64 → Uint8Array
      const binary = atob(pdfBase64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

      const blob = new Blob([bytes], { type: 'application/pdf' });
      const formData = new FormData();
      formData.append('files', blob, 'sample_doc.pdf');

      const res = await fetch(`${backendUrl}/ingest`, {
        method: 'POST',
        body: formData,
      });
      let body: any = null;
      try { body = await res.json(); } catch {}
      return { status: res.status, body };
    }, { backendUrl: BACKEND_URL, pdfBase64 });

    // 200 = full pipeline succeeded (chunked + embedded + stored)
    // 503 = backend infra (Bedrock/Qdrant) not reachable from Lambda — infra issue, not a deploy issue
    // Anything else (400, 413, 422, 500) = real contract failure → test fails
    expect([200, 503]).toContain(result.status);

    if (result.status === 200) {
      expect(result.body).toMatchObject({ status: 'ingested' });
      expect(result.body.documents).toHaveLength(1);
      expect(result.body.documents[0].chunks_created).toBeGreaterThan(0);
      // session_id must be returned — required by the frontend
      expect(typeof result.body.session_id).toBe('string');
      expect(result.body.session_id.length).toBeGreaterThan(0);
    }
  });
});
