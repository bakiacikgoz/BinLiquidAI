import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('target evidence closure is visible without primary raw JSON exposure', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });

  await openPrimaryView(page, 'Dashboard', 'Dashboard');
  const primary = page.getByTestId('page-primary-region');

  await expect(primary).toContainText('Target Evidence Closure');
  await expect(primary).toContainText('hash_only');
  await expect(primary).toContainText('raw_persistence_off');
  await expect(primary).toContainText('public-desktop-installer');
  await expect(primary).toContainText('Operator Attestation');
  await expect(primary).not.toContainText('{');

  consoleHealth.assertNoCriticalErrors();
});
