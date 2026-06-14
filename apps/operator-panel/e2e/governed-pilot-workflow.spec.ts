import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('governed pilot workflow page renders closure proof without raw payloads', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });

  await openPrimaryView(page, 'Governed Pilot Workflow', 'Governed Pilot Workflow');

  const workflow = page.getByTestId('governed-pilot-workflow');
  await expect(workflow).toContainText('hash_only');
  await expect(workflow).toContainText('deterministic');
  await expect(workflow).toContainText('public-desktop-installer');
  await expect(workflow).not.toContainText('Draft a remediation plan');
  await expect(workflow).not.toContainText('raw query');

  consoleHealth.assertNoCriticalErrors();
});
