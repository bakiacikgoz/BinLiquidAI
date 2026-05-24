import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView, operationOutput } from './helpers';

test('operations workspace runs safe preview operation tabs', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });
  await openPrimaryView(page, 'Yürütmeler', 'Operations');

  await page.getByRole('button', { name: 'Who am I', exact: true }).click();
  await expect(operationOutput(page)).toContainText('qa-operator');

  await page.getByLabel('Permission').fill('runtime.audit');
  await page.getByRole('button', { name: 'Check permission', exact: true }).click();
  await expect(operationOutput(page)).toContainText('runtime.audit');

  await page.getByRole('button', { name: 'Qualification', exact: true }).click();
  await page.getByRole('button', { name: 'Metrics snapshot', exact: true }).click();
  await expect(operationOutput(page)).toContainText('job_counts');
  await page.getByRole('button', { name: 'GA readiness', exact: true }).click();
  await expect(operationOutput(page)).toContainText('go_no_go');
  await page.getByRole('button', { name: 'Run qualification', exact: true }).click();
  await expect(operationOutput(page)).toContainText('qualification_status');

  await page.getByRole('button', { name: 'Security', exact: true }).click();
  await page.getByRole('button', { name: 'Security baseline', exact: true }).click();
  await expect(operationOutput(page)).toContainText('overall_status');

  await page.getByRole('button', { name: 'Keys', exact: true }).click();
  await page.getByRole('button', { name: 'Keys status', exact: true }).click();
  await expect(operationOutput(page)).toContainText('enterprise-signing-current');

  await page.getByRole('button', { name: 'Support', exact: true }).click();
  await page.getByRole('button', { name: 'Export support bundle', exact: true }).click();
  await expect(operationOutput(page)).toContainText('archive_path');

  await page.getByRole('button', { name: 'Backup / Restore / Migrate', exact: true }).click();
  await page.getByRole('button', { name: 'Create backup', exact: true }).click();
  await expect(operationOutput(page)).toContainText('backup_dir');
  await page.getByRole('button', { name: 'Migrate dry-run', exact: true }).click();
  await expect(operationOutput(page)).toContainText('dry_run');

  consoleHealth.assertNoCriticalErrors();
});
