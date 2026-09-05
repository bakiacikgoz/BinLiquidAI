import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('core tasks omit optional desktop execution', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });
  await openPrimaryView(page, 'Görevler', 'Tasks');

  const startSession = page.getByRole('button', { name: 'Start session', exact: true });
  const operationsCard = page.locator('.computer-use-operations-card');
  await expect(startSession).toHaveCount(0);
  await expect(operationsCard).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Submit run', exact: true }).first()).toBeVisible();

  consoleHealth.assertNoCriticalErrors();
});
