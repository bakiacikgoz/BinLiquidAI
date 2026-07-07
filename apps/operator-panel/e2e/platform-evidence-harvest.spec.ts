import { expect, test } from '@playwright/test';

import { expectNoHorizontalOverflow, gotoOperatorPanel } from './helpers';

test('platform evidence harvest route shows source install claim and target actions', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { profile: 'enterprise' });

  await page
    .getByRole('navigation', { name: 'Ana navigasyon' })
    .getByRole('button', { name: 'Platform Evidence', exact: true })
    .click();

  await expect(page.getByTestId('platform-evidence-harvest-view')).toBeVisible();
  await expect(page.getByTestId('source-install-rc-claim-view')).toBeVisible();
  await expect(page.getByTestId('target-closure-actions-view')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Source Install RC', exact: true })).toBeVisible();
  await expect(page.getByText('windows-x64 source-local-install evidenced')).toBeVisible();
  await expect(
    page.getByTestId('target-closure-actions-view').getByRole('cell', { name: 'darwin-arm64' }),
  ).toBeVisible();
  await expect(page.getByText(/all platforms ready/i)).toHaveCount(0);

  await expectNoHorizontalOverflow(page, 'platform evidence harvest');
  consoleHealth.assertNoCriticalErrors();
});
