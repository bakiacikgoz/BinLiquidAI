import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('system workspace refreshes doctor and config preview data', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page);
  await openPrimaryView(page, 'Sistem Sağlığı', 'System');

  await expect(page.getByRole('heading', { name: 'Doctor', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Effective config', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Capabilities', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Capability contract', exact: true })).toBeVisible();
  await expect(
    page
      .locator('.metric-card')
      .filter({ has: page.getByRole('heading', { name: 'Core version', exact: true }) }),
  ).toContainText('0.6.0-preview');

  await page.getByRole('button', { name: 'Refresh doctor', exact: true }).click();
  await page.getByRole('button', { name: 'Refresh config', exact: true }).click();
  await expect(page.getByText('qwen3.5:4b')).toBeVisible();

  consoleHealth.assertNoCriticalErrors();
});
