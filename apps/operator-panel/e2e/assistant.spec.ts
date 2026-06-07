import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('AI Assistant model selection is visible and used before sending a preview message', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });
  await openPrimaryView(page, 'AI Assistant', 'Welcome to AegisOS Assistant');

  const disabledSearch = page.getByRole('textbox', { name: 'Search' });
  await expect(disabledSearch).toBeDisabled();
  await expect(disabledSearch).toHaveAttribute('title', 'Assistant context search is not available yet');

  await page.getByLabel('Assistant provider').selectOption('ollama');
  await page.getByLabel('Assistant model', { exact: true }).selectOption('qwen3.5:4b');
  await page.getByLabel('Assistant fallback provider').selectOption('transformers');

  await expect(page.getByLabel('Selected assistant model')).toContainText('ollama / qwen3.5:4b');
  const desktopContextRail = page.locator('.assistant-context-rail-desktop').getByLabel('Assistant context rail');
  if (await desktopContextRail.isVisible()) {
    await expect(desktopContextRail.getByText('Assistant Runtime')).toBeVisible();
    await expect(desktopContextRail.getByText('Effective', { exact: true })).toBeVisible();
  } else {
    await page.getByRole('button', { name: 'Open assistant context' }).click();
    const contextPanel = page.getByRole('complementary', { name: 'Assistant context panel' });
    await expect(contextPanel.getByText('Assistant Runtime')).toBeVisible();
    await expect(contextPanel.getByText('Effective', { exact: true })).toBeVisible();
    await contextPanel.getByLabel('Close assistant context').click();
  }

  await page.getByLabel('Message').fill('Summarize the active run safely.');
  await page.getByLabel('Message').press('Enter');

  await expect(page.getByText('Summarize the active run safely.')).toBeVisible();
  await expect(page.getByText('The selected run is blocked by an approval gate.')).toBeVisible();
  await expect
    .poll(async () => {
      return page.evaluate(() => {
        const transcript = document.querySelector('.assistant-transcript');
        const composer = document.querySelector('.assistant-composer');
        const turns = Array.from(document.querySelectorAll('.assistant-turn'));
        const lastTurn = turns.at(-1);
        if (!transcript || !composer || !lastTurn) {
          return { composerOverlapsTranscript: true, lastTurnStartsBehindComposer: true, forcedToBottom: true };
        }
        const transcriptRect = transcript.getBoundingClientRect();
        const composerRect = composer.getBoundingClientRect();
        const lastTurnRect = lastTurn.getBoundingClientRect();
        const maxScrollTop = Math.max(0, transcript.scrollHeight - transcript.clientHeight);
        return {
          composerOverlapsTranscript: composerRect.top < transcriptRect.bottom - 1,
          lastTurnStartsBehindComposer:
            lastTurnRect.top < transcriptRect.top - 1 || lastTurnRect.top >= composerRect.top - 1,
          forcedToBottom: maxScrollTop > 24 && transcript.scrollTop >= maxScrollTop - 8,
        };
      });
    })
    .toEqual({ composerOverlapsTranscript: false, lastTurnStartsBehindComposer: false, forcedToBottom: false });
  await expect(page.getByLabel('Selected assistant model')).toContainText('ollama / qwen3.5:4b');
  consoleHealth.assertNoCriticalErrors();
});
