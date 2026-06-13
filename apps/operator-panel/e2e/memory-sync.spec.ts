import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('memory sync status is visible behind runtime route', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });

  await openPrimaryView(page, 'Memory Runtime', 'Memory Runtime');

  const syncStatus = page.getByTestId('memory-sync-status');
  await expect(syncStatus).toContainText('Apply approval gate');
  await expect(syncStatus).toContainText('Cross-environment import');

  consoleHealth.assertNoCriticalErrors();
});
