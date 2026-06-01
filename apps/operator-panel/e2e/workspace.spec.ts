import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, saveE2eScreenshot } from './helpers';

test('workspace smoke renders preview mission control without critical console errors', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page);

  await expect(page.getByRole('heading', { name: 'Mission Control', exact: true })).toBeVisible();
  await expect(page.getByTestId('runtime-truth-banner')).toContainText('preview_fixture');
  await expect(page.getByTestId('runtime-truth-banner')).toContainText('Preview fixture data');
  await expect(page.locator('.system-health-card')).toContainText('SİSTEM SAĞLIĞI');
  await expect(page.getByLabel('Computer-use capability')).toBeVisible();
  await expect(page.getByText('MACOS_COMPUTER_USE_NOT_QUALIFIED', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: /Onayla ve Devam Et/i })).toBeDisabled();
  await expect(page.getByRole('button', { name: /Onayla ve Devam Et/i })).toHaveAttribute(
    'title',
    'Set operator id to continue',
  );

  await saveE2eScreenshot(page, 'workspace-desktop');
  consoleHealth.assertNoCriticalErrors();
});
