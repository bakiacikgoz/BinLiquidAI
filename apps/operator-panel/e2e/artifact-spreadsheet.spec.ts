import { expect, test } from '@playwright/test';

import { installStructuredArtifactBridgeStub, structuredArtifactCommands } from './artifact-helpers';
import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('spreadsheet forced-off fallback stays read-only and exports injection-safe CSV/XLSX', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'spreadsheet-operator' });
  await openPrimaryView(page, 'AI Assistant', 'Welcome to ImperaOS Assistant');
  await page.getByLabel('Message').fill('Open a governed spreadsheet artifact.');
  await page.getByLabel('Message').press('Enter');
  await expect(page.getByRole('button', { name: 'Open Launch plan' })).toBeVisible();
  await installStructuredArtifactBridgeStub(page, 'spreadsheet');
  await page.getByRole('button', { name: 'Open Launch plan' }).dispatchEvent('click');

  const workbench = page.getByRole('complementary', { name: 'Workbench' });
  await expect(workbench.getByRole('region', { name: 'spreadsheet read-only fallback' })).toBeVisible();
  await expect(workbench.getByText('"A1": "[truncated]"', { exact: false })).toBeVisible();
  await expect(workbench.getByRole('textbox')).toHaveCount(0);
  await workbench.getByRole('button', { name: 'Export Budget CSV' }).click();
  await expect.poll(async () => (await structuredArtifactCommands(page)).filter((item) => item.includes('export')))
    .toEqual(['bridge_artifact_export_begin', 'bridge_artifact_export_commit']);
  const exportedCsv = await page.evaluate(() => {
    const state = (window as unknown as {
      __structuredArtifactE2eState: { snapshot(): { exportedBytes: number[] } };
    }).__structuredArtifactE2eState;
    return new TextDecoder().decode(new Uint8Array(state.snapshot().exportedBytes));
  });
  expect(exportedCsv).toContain("'=1+1");
  expect(await structuredArtifactCommands(page)).not.toContain('bridge_artifact_mutate');
  consoleHealth.assertNoCriticalErrors();
});
