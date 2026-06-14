import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('design partner handoff page renders release handoff without raw payloads', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });

  await openPrimaryView(page, 'Design Partner Handoff', 'Design Partner Handoff');

  const handoff = page.getByTestId('design-partner-handoff');
  await expect(handoff).toContainText('release_train_pass');
  await expect(handoff).toContainText('first_run_pass');
  await expect(handoff).toContainText('publicDesktop');
  await expect(handoff).toContainText('blocked');
  await expect(handoff).not.toContainText('BEGIN RAW');
  await expect(handoff).not.toContainText('Draft a remediation plan');

  consoleHealth.assertNoCriticalErrors();
});
