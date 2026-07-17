import { expect, test } from '@playwright/test';

import { installStructuredArtifactBridgeStub, structuredArtifactCommands } from './artifact-helpers';
import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('canvas forced-off fallback renders bounded local data and exports safe JSON', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'canvas-operator' });
  await openPrimaryView(page, 'AI Assistant', 'Welcome to ImperaOS Assistant');
  await page.getByLabel('Message').fill('Open a governed canvas artifact.');
  await page.getByLabel('Message').press('Enter');
  await expect(page.getByRole('button', { name: 'Open Launch plan' })).toBeVisible();
  await installStructuredArtifactBridgeStub(page, 'canvas');
  await page.getByRole('button', { name: 'Open Launch plan' }).dispatchEvent('click');

  const workbench = page.getByRole('complementary', { name: 'Workbench' });
  const fallback = workbench.getByRole('region', { name: 'canvas read-only fallback' });
  await expect(fallback).toBeVisible();
  await expect(fallback.getByText('<script>local text only</script>', { exact: false })).toBeVisible();
  await fallback.getByRole('button', { name: 'Export SVG' }).click();
  await expect.poll(async () => (await structuredArtifactCommands(page)).filter((item) => item.includes('export')))
    .toEqual(['bridge_artifact_export_begin', 'bridge_artifact_export_commit']);
  expect(await structuredArtifactCommands(page)).not.toContain('bridge_artifact_mutate');
  consoleHealth.assertNoCriticalErrors();
});
