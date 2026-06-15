import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('mainline rc freeze page renders freeze evidence without raw payloads', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });

  await openPrimaryView(page, 'Mainline RC Freeze', 'Mainline RC Freeze');

  const freeze = page.getByTestId('mainline-rc-freeze');
  await expect(freeze).toContainText(/stack_|not generated/);
  await expect(freeze).toContainText('hash_only');
  await expect(freeze).toContainText('raw persistence false');
  await expect(freeze).not.toContainText('BEGIN RAW');
  await expect(freeze).not.toContainText('rawPayload');

  consoleHealth.assertNoCriticalErrors();
});
