import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('design partner field evidence page renders strict RC closure without raw payloads', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });

  await openPrimaryView(page, 'Design Partner Field Evidence', 'Design Partner Field Evidence');

  const fieldEvidence = page.getByTestId('design-partner-field-evidence');
  await expect(fieldEvidence).toContainText('hash_only');
  await expect(fieldEvidence).toContainText('attestation_valid');
  await expect(fieldEvidence).toContainText('strict_rc_ready');
  await expect(fieldEvidence).toContainText('public-desktop-installer');
  await expect(fieldEvidence).not.toContainText('BEGIN RAW');
  await expect(fieldEvidence).not.toContainText('Draft a remediation plan');

  consoleHealth.assertNoCriticalErrors();
});
