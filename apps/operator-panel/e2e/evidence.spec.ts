import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('evidence workspace verifies the latest preview evidence pack', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });
  await openPrimaryView(page, 'Evidence', 'Signed Evidence');

  await expect(page.getByRole('heading', { name: 'Evidence packs', exact: true })).toBeVisible();
  await expect(page.getByText('evp-preview-run', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Verify latest', exact: true }).click();

  await expect(page.getByText('Evidence verification completed')).toBeVisible();
  await expect(page.locator('.evidence-pack-view')).toContainText('pass');
  await expect(page.locator('.evidence-pack-view')).toContainText('passed');

  consoleHealth.assertNoCriticalErrors();
});
