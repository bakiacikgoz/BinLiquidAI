import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('AI Assistant tasking proposal can be submitted with confirmed plan hash', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator', profile: 'enterprise' });
  await openPrimaryView(page, 'AI Assistant', 'Welcome to AegisOS Assistant');

  await page.getByLabel('Message').fill('External Gateway Agent should open a follow-up support ticket.');
  await page.getByLabel('Message').press('Enter');

  await expect(page.getByText('Governed task proposal')).toBeVisible();
  await expect(page.getByText('Open a governed external support ticket')).toBeVisible();
  await expect(page.getByText('ASSISTANT_TASK_WRITE_REQUIRES_APPROVAL').first()).toBeVisible();
  await expect(page.getByText(/confirmPlanHash sha256:/)).toBeVisible();

  await page.getByRole('button', { name: 'Submit with plan hash' }).click();

  await expect(page.getByText('Task submission')).toBeVisible();
  await expect(page.getByText('blocked pending approval')).toBeVisible();
  await expect(page.getByText('agt-preview-001').first()).toBeVisible();
  await expect(page.getByText('apr-preview-task-001')).toBeVisible();
  await expect(page.getByText('Raw JSON')).toHaveCount(0);
  consoleHealth.assertNoCriticalErrors();
});
