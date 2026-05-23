import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('approval mutation controls are disabled without an operator id', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page);
  await openPrimaryView(page, 'Onaylar', 'Approvals');

  await expect(page.getByRole('button', { name: 'Approve', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Reject', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Execute', exact: true })).toBeDisabled();

  consoleHealth.assertNoCriticalErrors();
});

test('approval lifecycle approves and executes a pending preview approval', async ({ page }) => {
  const dialogMessages: string[] = [];
  page.on('dialog', async (dialog) => {
    dialogMessages.push(dialog.message());
    await dialog.accept();
  });

  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });
  await openPrimaryView(page, 'Onaylar', 'Approvals');

  await expect(
    page.locator('.list-scroll').getByRole('button').filter({ hasText: 'apr_20260308_device_action' }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Approve', exact: true }).click();
  await expect(page.getByText('Approve OK')).toBeVisible();

  await page.getByRole('button', { name: 'Execute', exact: true }).click();
  await expect(page.getByText('Execute OK')).toBeVisible();
  expect(dialogMessages.some((message) => message.includes('ui:qa-operator'))).toBe(true);
  expect(dialogMessages.some((message) => message.includes('apr_20260308_device_action'))).toBe(true);

  consoleHealth.assertNoCriticalErrors();
});
