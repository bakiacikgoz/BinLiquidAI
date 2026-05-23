import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('tasks submit flow uses preview bridge and exposes the submitted run', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });
  await openPrimaryView(page, 'Görevler', 'Tasks');

  await page.getByLabel('Spec path').fill('examples/team/restricted_pilot.yaml');
  await page.getByLabel('Request').fill('Inspect the queue safely from browser E2E.');

  const readiness = page
    .locator('article.page-card')
    .filter({ has: page.getByRole('heading', { name: 'Submit readiness', exact: true }) });
  await readiness.getByRole('button', { name: 'Submit run', exact: true }).click();

  await expect(page.getByText('Submit run OK')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Mission Control', exact: true })).toBeVisible();
  await expect(page.locator('.selected-run-card')).toContainText('job-ui-preview-1');

  await openPrimaryView(page, 'Çalıştırmalar', 'Runs');
  await expect(page.locator('.selected-run-card')).toContainText('job-ui-preview-1');
  consoleHealth.assertNoCriticalErrors();
});
