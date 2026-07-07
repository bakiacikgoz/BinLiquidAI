import { expect, test } from '@playwright/test';

import { expectNoHorizontalOverflow, gotoOperatorPanel } from './helpers';

test('local product platform evidence page renders handoff state without raw payloads', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { profile: 'enterprise' });

  await page
    .getByRole('navigation', { name: 'Ana navigasyon' })
    .getByRole('button', { name: 'Platform Evidence', exact: true })
    .click();

  await expect(page.getByTestId('platform-evidence-view')).toBeVisible();
  await expect(page.getByTestId('rc-handoff-view')).toBeVisible();
  await expect(
    page.getByTestId('platform-evidence-view').getByRole('cell', { name: 'windows-x64' }),
  ).toBeVisible();
  await expect(page.getByRole('cell', { name: 'linux-x64' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Platform Evidence', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'RC Handoff', exact: true })).toBeVisible();
  await expect(page.getByText(/rawPayload|providerPayload/i)).toHaveCount(0);

  await expectNoHorizontalOverflow(page, 'local product platform evidence');
  consoleHealth.assertNoCriticalErrors();
});
