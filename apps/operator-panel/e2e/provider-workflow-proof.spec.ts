import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('provider workflow proof is visible without primary raw JSON exposure', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });

  await openPrimaryView(page, 'Dashboard', 'Dashboard');
  const primary = page.getByTestId('page-primary-region');

  await expect(primary).toContainText('Provider Trust');
  await expect(primary).toContainText('Provider Execution Evidence');
  await expect(primary).toContainText('dry_run');
  await expect(primary).toContainText('hash_only');
  await expect(primary).toContainText('raw_persistence_off');
  await expect(primary).toContainText('Workflow Proof');
  await expect(primary).toContainText('executed_mutations=0');
  await expect(primary).not.toContainText('{');

  consoleHealth.assertNoCriticalErrors();
});
