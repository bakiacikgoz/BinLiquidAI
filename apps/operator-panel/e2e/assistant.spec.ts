import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('AI Assistant model selection is visible and used before sending a preview message', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });
  await openPrimaryView(page, 'AI Assistant', 'Welcome to AegisOS Assistant');

  const disabledSearch = page.getByRole('textbox', { name: 'Search assistant context' });
  await expect(disabledSearch).toBeDisabled();
  await expect(disabledSearch).toHaveAttribute('title', 'Assistant context search is not available yet');

  await page.getByLabel('Assistant provider').selectOption('ollama');
  await page.getByRole('textbox', { name: 'Assistant model', exact: true }).fill('qwen3.5:4b');
  await page.getByLabel('Assistant fallback provider').selectOption('transformers');

  await expect(page.getByLabel('Selected assistant model')).toContainText('ollama / qwen3.5:4b');
  await expect(page.getByText('Assistant Runtime')).toBeVisible();
  await expect(page.getByLabel('Assistant context rail').getByText('Effective', { exact: true })).toBeVisible();

  await page.getByLabel('Message').fill('Summarize the active run safely.');
  await page.getByRole('button', { name: 'Send' }).click();

  await expect(page.getByText('Summarize the active run safely.')).toBeVisible();
  await expect(page.getByLabel('Selected assistant model')).toContainText('ollama / qwen3.5:4b');
  consoleHealth.assertNoCriticalErrors();
});
