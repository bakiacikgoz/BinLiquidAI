import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('computer-use start remains blocked when vision runtime is not qualified', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });
  await openPrimaryView(page, 'Görevler', 'Tasks');

  const startSession = page.getByRole('button', { name: 'Start session', exact: true });
  const operationsCard = page.locator('.computer-use-operations-card');
  await expect(startSession).toBeDisabled();
  await expect(startSession).toHaveAttribute('title', /Computer-use vision runtime blocked/);
  await expect(operationsCard.getByLabel('Computer-use blockers')).toContainText('MACOS_COMPUTER_USE_NOT_QUALIFIED');
  await expect(operationsCard).toContainText('Run doctor/preflight; do not start live automation.');

  consoleHealth.assertNoCriticalErrors();
});
