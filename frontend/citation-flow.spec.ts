import { test, expect } from '@playwright/test';

/**
 * These three tests map directly to RULES.md "End-to-End (Playwright)":
 *   - test_happy_path_question_shows_citation_and_highlights_source
 *   - test_adversarial_question_shows_refusal_not_error_state
 *   - test_citation_click_scrolls_and_highlights_correct_page
 *
 * FILL IN the two constants below once you've picked your demo
 * document set (MEMORY.md "Hour 0" entry). A known-answerable
 * question and a known-adversarial question, both specific to your
 * actual uploaded documents, are required — generic placeholders
 * here will not exercise the real retrieval/verification pipeline.
 */

const ANSWERABLE_QUESTION = 'REPLACE_WITH_A_REAL_QUESTION_YOUR_DOCS_ANSWER';
const EXPECTED_PAGE_NUMBER = 'REPLACE_WITH_EXPECTED_PAGE_NUMBER'; // e.g. '12'

const ADVERSARIAL_QUESTION = 'REPLACE_WITH_A_QUESTION_YOUR_DOCS_DO_NOT_ANSWER';

test.describe('Citation-grounded QA — core guardrail behavior', () => {
  test('happy path: answerable question shows citation and highlights source', async ({ page }) => {
    await page.goto('/');

    const input = page.getByRole('textbox', { name: /ask a question/i });
    await input.fill(ANSWERABLE_QUESTION);
    await input.press('Enter');

    // Answer bubble should appear, not a refusal bubble.
    const answerBubble = page.getByTestId('answer-bubble').first();
    await expect(answerBubble).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId('refusal-bubble')).not.toBeVisible();

    // At least one citation chip must be present — an "answered"
    // response with zero citations would violate DECISION.md Rule 5
    // (should have been a refusal instead), so this assertion is
    // also an implicit contract check on the backend, not just UI.
    const citationChip = page.getByTestId('citation-chip').first();
    await expect(citationChip).toBeVisible();
    await expect(citationChip).toContainText(EXPECTED_PAGE_NUMBER);

    // Clicking the chip should highlight the source viewer.
    await citationChip.click();
    const sourceViewer = page.getByTestId('source-viewer');
    await expect(sourceViewer).toBeVisible();
    await expect(page.getByTestId('citation-highlight')).toBeVisible({
      timeout: 5_000,
    });
  });

  test('adversarial question shows refusal, not an error state', async ({ page }) => {
    await page.goto('/');

    const input = page.getByRole('textbox', { name: /ask a question/i });
    await input.fill(ADVERSARIAL_QUESTION);
    await input.press('Enter');

    // Refusal bubble should appear — distinctly, not as an error toast
    // or a blank/broken state (UI-UX.md: refusal is a correct
    // behavior, not a failure, and must look like one).
    const refusalBubble = page.getByTestId('refusal-bubble').first();
    await expect(refusalBubble).toBeVisible({ timeout: 15_000 });

    // Must NOT render as a generic error UI element.
    await expect(page.getByTestId('error-toast')).not.toBeVisible();
    await expect(page.getByTestId('answer-bubble')).not.toBeVisible();

    // No citation chips should appear on a refusal — zero surviving
    // citations is exactly what triggers the refusal path.
    await expect(page.getByTestId('citation-chip')).toHaveCount(0);
  });

  test('citation click scrolls to and highlights the correct page', async ({ page }) => {
    await page.goto('/');

    const input = page.getByRole('textbox', { name: /ask a question/i });
    await input.fill(ANSWERABLE_QUESTION);
    await input.press('Enter');

    const citationChip = page.getByTestId('citation-chip').first();
    await expect(citationChip).toBeVisible({ timeout: 15_000 });
    await citationChip.click();

    const pageIndicator = page.getByTestId('page-nav-current');
    await expect(pageIndicator).toHaveText(EXPECTED_PAGE_NUMBER, {
      timeout: 5_000,
    });

    const highlight = page.getByTestId('citation-highlight');
    await expect(highlight).toBeVisible();
  });
});
