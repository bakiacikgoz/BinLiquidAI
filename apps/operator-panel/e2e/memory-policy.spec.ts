import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('memory runtime policy page surface renders hash-only enforcement posture', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });

  await openPrimaryView(page, 'Memory Runtime', 'Memory Runtime');

  const policy = page.getByTestId('memory-policy-enforcement');
  await expect(policy).toContainText('Memory Policy Enforcement');
  await expect(policy).toContainText('Semantic mode');
  await expect(policy).toContainText('Raw leaks');
  await expect(policy).not.toContainText('raw query');

  consoleHealth.assertNoCriticalErrors();
});
