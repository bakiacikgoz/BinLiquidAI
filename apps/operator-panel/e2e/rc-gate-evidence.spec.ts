import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('rc gate evidence page renders ledger readiness without raw payloads', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });

  await openPrimaryView(page, 'RC Gate Evidence', 'RC Gate Evidence');

  const evidence = page.getByTestId('rc-gate-evidence');
  await expect(evidence).toContainText(/ready|missing|conditional/);
  await expect(evidence).toContainText(/Ready for RC freeze:/);
  await expect(evidence).toContainText(/Make required:/);
  await expect(evidence).not.toContainText('BEGIN RAW');
  await expect(evidence).not.toContainText('rawPayload');

  consoleHealth.assertNoCriticalErrors();
});
