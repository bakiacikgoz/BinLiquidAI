import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('pilot launch candidate state is visible across readiness, evidence, operations, and admin pages', async ({
  page,
}) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });

  await openPrimaryView(page, 'Dashboard', 'Dashboard');
  await expect(page.getByTestId('page-primary-region')).toContainText('Pilot Launch Candidate');
  await expect(page.getByTestId('page-primary-region')).toContainText('Enterprise Hat A');

  await openPrimaryView(page, 'Sistem Sağlığı', 'System');
  await expect(page.getByTestId('page-primary-region')).toContainText('Pilot Launch Candidate');
  await expect(page.getByTestId('page-primary-region')).toContainText('Install rehearsal');

  await openPrimaryView(page, 'Evidence', 'Signed Evidence');
  await expect(page.getByTestId('page-primary-region')).toContainText('Evidence corpus');
  await expect(page.getByTestId('page-primary-region')).toContainText('Enterprise Hat A');

  await openPrimaryView(page, 'Raporlar', 'Reports');
  await expect(page.getByTestId('page-primary-region')).toContainText('Pilot Launch Candidate');
  await expect(page.getByTestId('page-primary-region')).toContainText('Pilot metrics');

  await openPrimaryView(page, 'Yürütmeler', 'Operations');
  await page.getByRole('button', { name: 'Qualification', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Install rehearsal', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Security', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Security review', exact: true })).toBeVisible();

  await openPrimaryView(page, 'Kullanıcılar', 'Users');
  await expect(page.getByTestId('page-primary-region')).toContainText('Admin proposals');

  await openPrimaryView(page, 'Roller', 'Roles');
  await expect(page.getByTestId('page-primary-region')).toContainText('update proposal');

  await openPrimaryView(page, 'Politikalar', 'Policy Packs');
  await expect(page.getByTestId('page-primary-region')).toContainText('promote proposal');

  consoleHealth.assertNoCriticalErrors();
});
