import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('memory governance page renders guarded snapshot signals', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });

  await openPrimaryView(page, 'Memory Governance', 'Memory Governance');

  const region = page.getByTestId('page-primary-region');
  await expect(region).toContainText('Authority status');
  await expect(region).toContainText('raw_persistence_off');
  await expect(region).toContainText('hash_only_redacted');

  consoleHealth.assertNoCriticalErrors();
});
