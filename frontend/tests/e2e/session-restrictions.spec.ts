import { test, expect } from '@playwright/test';

test.describe('Session ID Restrictions and Sanitization', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  test('App loads to Document Upload screen when no session_id is in store', async ({ page }) => {
    // When no session_id exists, upload dropzone / screen must be shown
    const fileInput = page.getByTestId('file-input');
    await expect(fileInput).toBeAttached({ timeout: 5000 });
    await expect(page.getByText('Add your documents')).toBeVisible();

    // Source viewer / chat layout must NOT be visible
    await expect(page.getByTestId('source-viewer')).not.toBeVisible();
  });

  test('Persisting invalid or missing session_id forces upload view', async ({ page }) => {
    // Set localStorage with currentView: 'chat' but sessionId: null
    await page.evaluate(() => {
      localStorage.setItem(
        'cited-or-silent-store',
        JSON.stringify({
          state: {
            sessionId: null,
            currentView: 'chat',
            documents: [],
            messages: [],
            ingestionPhase: 'idle',
          },
          version: 0,
        })
      );
    });

    await page.reload();

    // Must still show the upload screen because sessionId is null
    await expect(page.getByText('Add your documents')).toBeVisible();
    await expect(page.getByTestId('source-viewer')).not.toBeVisible();
  });

  test('Send button is disabled when input is empty and enabled when query input is provided with valid session', async ({ page }) => {
    // Set localStorage with valid sessionId and currentView: 'chat'
    await page.evaluate(() => {
      localStorage.setItem(
        'cited-or-silent-store',
        JSON.stringify({
          state: {
            sessionId: 'valid_session_123',
            currentView: 'chat',
            documents: [{ filename: 'test.pdf', chunks_created: 5, pages: 2 }],
            messages: [],
            ingestionPhase: 'done',
          },
          version: 0,
        })
      );
    });

    await page.reload();

    const input = page.getByPlaceholder('Ask a question...');
    await expect(input).toBeVisible();
    await expect(input).toBeEnabled();

    const sendBtn = page.getByRole('button', { name: /send/i });
    // Empty input: disabled
    await expect(sendBtn).toBeDisabled();

    // Fill input: enabled
    await input.fill('What is deep learning?');
    await expect(sendBtn).toBeEnabled();
  });
});
