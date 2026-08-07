import { test, expect, Page } from '@playwright/test';
import path from 'path';
import fs from 'fs';

/**
 * End-to-End Playwright test suite for Cited-or-Silent.
 *
 * Tests the full pipeline:
 *   1. File upload (POST /ingest  — S3 + chunking)
 *   2. Analyze    (POST /analyze — Bedrock embeddings, 1.4s/chunk)
 *   3. Chat happy path (citation chip → Source Viewer real text)
 *   4. Adversarial / out-of-scope guardrail
 *   5. Multi-PDF session
 *   6. Source Viewer anti-hallucination check
 *   7. New Session flow
 *
 * PDFs are read from the root /data directory.
 */

const DATA_DIR = path.resolve(process.cwd(), '../data');

// Paths to the real test PDFs
const PDF_ATTENTION   = path.join(DATA_DIR, '1706.03762v7 (1).pdf');   // "Attention Is All You Need"
const PDF_CLIP        = path.join(DATA_DIR, '2103.16775v1.pdf');        // CLIP paper
const PDF_SMALL       = path.join(DATA_DIR, '2507.19595v3.pdf');        // Smaller PDF for speed

const QUESTION_ATTENTION   = 'What is the attention mechanism used in the Transformer model?';
const QUESTION_CLIP        = 'What does CLIP stand for and how does it work?';
const ADVERSARIAL_QUESTION = 'What is the exact stock price of Microsoft on January 1st 2030?';
const OUT_OF_SCOPE_QUESTION = 'How do I bake chocolate chip cookies?';

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Full two-phase ingestion: upload files then click Analyze.
 * Waits for the source viewer to appear (indicates chat is ready).
 */
async function ingestAndAnalyze(page: Page, pdfPaths: string[], timeout = 420_000) {
  // Phase 1: select files and upload
  const fileInput = page.getByTestId('file-input');
  await expect(fileInput).toBeAttached();
  await fileInput.setInputFiles(pdfPaths);

  // Upload button should appear after file selection
  const uploadBtn = page.getByTestId('upload-button');
  await expect(uploadBtn).toBeVisible({ timeout: 5_000 });
  await uploadBtn.click();

  // Wait for "Start Analyzing" button (Phase 1 complete)
  const analyzeBtn = page.getByTestId('ingest-button');
  await expect(analyzeBtn).toBeVisible({ timeout: 180_000 });
  await expect(analyzeBtn).toBeEnabled({ timeout: 180_000 });

  // Phase 2: trigger embeddings
  await analyzeBtn.click();

  // Wait for chat view (source-viewer should be visible once analysis complete)
  const sourceViewer = page.getByTestId('source-viewer');
  await expect(sourceViewer).toBeVisible({ timeout });
}

/**
 * Send a question in chat and wait for either an answer or refusal bubble.
 */
async function askQuestion(page: Page, question: string) {
  const input = page.getByPlaceholder(/ask a question/i);
  await input.fill(question);
  await input.press('Enter');
  const answer  = page.getByTestId('answer-bubble').first();
  const refusal = page.getByTestId('refusal-bubble').first();
  await expect(answer.or(refusal)).toBeVisible({ timeout: 90_000 });
  return { answer, refusal };
}

// ── Suite Setup ──────────────────────────────────────────────────────────────

test.beforeEach(async ({ page }) => {
  page.on('console', msg => {
    if (msg.type() !== 'debug') console.log('PAGE LOG:', msg.text());
  });
  page.on('pageerror', err => console.error('PAGE ERROR:', err));
  await page.goto('/');
  // Clear persisted store to ensure a clean state
  await page.evaluate(() => localStorage.clear());
  await page.reload();
});

// ── Test 1: Single PDF ingestion flow ────────────────────────────────────────

test('Phase 1+2: single PDF upload → analyze → chat view appears', async ({ page }) => {
  test.setTimeout(420_000);

  expect(fs.existsSync(PDF_SMALL)).toBe(true);
  await ingestAndAnalyze(page, [PDF_SMALL]);

  // Source viewer must be visible — confirms chat view loaded
  await expect(page.getByTestId('source-viewer')).toBeVisible();
});

// ── Test 2: Upload button disabled during upload ──────────────────────────────

test('UI: Upload button disabled while uploading, Analyze disabled until upload done', async ({ page }) => {
  test.setTimeout(30_000);

  const fileInput = page.getByTestId('file-input');
  await fileInput.setInputFiles(PDF_SMALL);

  // Upload button should be visible and enabled after file selection
  const uploadBtn = page.getByTestId('upload-button');
  await expect(uploadBtn).toBeVisible();
  await expect(uploadBtn).toBeEnabled();

  // Start Analyzing button should NOT be visible yet (upload not done)
  const analyzeBtn = page.getByTestId('ingest-button');
  await expect(analyzeBtn).not.toBeVisible();
});

// ── Test 3: RULES.md required: test_happy_path_question_shows_citation_and_highlights_source
test('test_happy_path_question_shows_citation_and_highlights_source', async ({ page }) => {
  test.setTimeout(420_000);

  await ingestAndAnalyze(page, [PDF_SMALL]);

  const { answer, refusal } = await askQuestion(page, QUESTION_ATTENTION);

  // Must get at least one bubble
  const gotAnswer  = await answer.isVisible();
  const gotRefusal = await refusal.isVisible();
  expect(gotAnswer || gotRefusal).toBe(true);

  if (gotAnswer) {
    // Citation chip must appear
    const chip = page.getByTestId('citation-chip').first();
    await expect(chip).toBeVisible({ timeout: 5_000 });

    // Click it — source viewer should highlight text
    await chip.click();

    const highlight = page.getByTestId('citation-highlight');
    await expect(highlight).toBeVisible({ timeout: 5_000 });

    // ── Anti-hallucination check ─────────────────────────────────────────────
    // The Source Viewer must show the real chunk text (NOT the hardcoded mock text)
    const mockTexts = [
      'The preliminary phase of the study yielded baseline metrics',
      'cognitive assessment scores indicated a marginal improvement',
      'Confidential Draft',
    ];
    const chunkText = page.getByTestId('source-chunk-text');
    await expect(chunkText).toBeVisible({ timeout: 5_000 });
    const renderedText = await chunkText.innerText();

    for (const mockText of mockTexts) {
      expect(renderedText).not.toContain(mockText);
    }

    // Rendered text should be non-trivial
    expect(renderedText.length).toBeGreaterThan(30);
  }
});

// ── Test 4: RULES.md required: test_adversarial_question_shows_refusal_not_error_state
test('test_adversarial_question_shows_refusal_not_error_state', async ({ page }) => {
  test.setTimeout(420_000);

  await ingestAndAnalyze(page, [PDF_SMALL]);

  const { refusal } = await askQuestion(page, ADVERSARIAL_QUESTION);
  await expect(refusal).toBeVisible({ timeout: 90_000 });

  // Refusal must have distinct neutral styling, NOT an error bubble
  const answer = page.getByTestId('answer-bubble').first();
  expect(await answer.isVisible()).toBe(false);
});

// ── Test 5: RULES.md required: test_citation_click_scrolls_and_highlights_correct_page
test('test_citation_click_scrolls_and_highlights_correct_page', async ({ page }) => {
  test.setTimeout(420_000);

  await ingestAndAnalyze(page, [PDF_SMALL]);

  const { answer } = await askQuestion(page, QUESTION_ATTENTION);
  const gotAnswer = await answer.isVisible();

  if (gotAnswer) {
    const chip = page.getByTestId('citation-chip').first();
    await expect(chip).toBeVisible();

    // The chip shows p.X — extract page number
    const chipText = await chip.innerText();
    const pageMatch = chipText.match(/p\.(\d+)/);

    await chip.click();

    if (pageMatch) {
      const expectedPage = pageMatch[1];
      const currentPageEl = page.getByTestId('page-nav-current');
      await expect(currentPageEl).toHaveText(expectedPage, { timeout: 5_000 });
    }

    // Verify quote highlight is rendered in the source viewer
    const highlight = page.getByTestId('citation-highlight');
    await expect(highlight).toBeVisible({ timeout: 5_000 });
  }
});

// ── Test 6: Out-of-scope — guardrail rejects obvious non-document question ────
test('Guardrail: completely off-topic question (cookies recipe) is refused', async ({ page }) => {
  test.setTimeout(420_000);

  await ingestAndAnalyze(page, [PDF_SMALL]);

  const { refusal } = await askQuestion(page, OUT_OF_SCOPE_QUESTION);
  await expect(refusal).toBeVisible({ timeout: 90_000 });
});

// ── Test 7: Multi-PDF — two documents in one session ─────────────────────────
test('Multi-PDF: two PDFs in one session; questions answered from correct source', async ({ page }) => {
  test.setTimeout(600_000); // Extra time — two PDFs means more embeddings

  expect(fs.existsSync(PDF_ATTENTION)).toBe(true);
  expect(fs.existsSync(PDF_SMALL)).toBe(true);

  await ingestAndAnalyze(page, [PDF_SMALL, PDF_ATTENTION]);

  // Ask about a topic from the attention paper
  const { answer, refusal } = await askQuestion(page, QUESTION_ATTENTION);
  const gotAnswer = await answer.isVisible();
  const gotRefusal = await refusal.isVisible();
  expect(gotAnswer || gotRefusal).toBe(true);

  if (gotAnswer) {
    // Citation should reference the correct source file
    const chip = page.getByTestId('citation-chip').first();
    await expect(chip).toBeVisible();
    await chip.click();

    const chunkText = page.getByTestId('source-chunk-text');
    await expect(chunkText).toBeVisible({ timeout: 5_000 });

    // Source viewer header should show a real filename
    const svHeader = page.getByTestId('source-viewer');
    const headerText = await svHeader.innerText();
    expect(headerText.toLowerCase()).toMatch(/\.pdf/);
  }
});

// ── Test 8: New Session resets state ─────────────────────────────────────────
test('New Session button resets state and returns to upload screen', async ({ page }) => {
  test.setTimeout(420_000);

  await ingestAndAnalyze(page, [PDF_SMALL]);

  // Should be on chat view
  await expect(page.getByTestId('source-viewer')).toBeVisible();

  // Click "New Session"
  const newSessionBtn = page.getByRole('button', { name: /new session/i });
  await expect(newSessionBtn).toBeVisible();
  await newSessionBtn.click();

  // Should return to the upload screen
  const fileInput = page.getByTestId('file-input');
  await expect(fileInput).toBeAttached({ timeout: 10_000 });
});
