import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('runs workspace exposes artifact, replay, and diagnostics tabs safely', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page);
  await openPrimaryView(page, 'Çalıştırmalar', 'Runs');

  await expect(page.locator('.list-scroll').getByRole('button').filter({ hasText: 'run_20260308_0910' })).toBeVisible();
  await page.getByRole('button', { name: 'Artifacts', exact: true }).click();

  const showRaw = page.getByRole('button', { name: 'Show raw', exact: true });
  await expect(showRaw).toBeDisabled();
  await expect(showRaw).toHaveAttribute('title', 'Ham payload modu ayarlardan açılmalı.');
  await expect(page.getByTestId('artifact-summary')).toContainText('contract_version');

  await page.getByRole('button', { name: 'Replay', exact: true }).click();
  await expect(page.getByTestId('run-replay-summary')).toContainText('audit-hash-preview');

  await page.getByRole('button', { name: 'Diagnostics', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Drift signals', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'System context', exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Export', exact: true }).click();
  await page.getByLabel('Export path').fill('./exports/e2e-runs');
  await page.getByRole('dialog').getByRole('button', { name: 'Export', exact: true }).click();
  await expect(page.getByText('Export completed')).toBeVisible();

  consoleHealth.assertNoCriticalErrors();
});
