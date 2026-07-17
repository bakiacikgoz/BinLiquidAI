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
  const fallback = workbench.getByRole('region', { name: 'spreadsheet read-only fallback' });
  const summary = fallback.getByLabel('spreadsheet bounded content summary');
  await expect(fallback).toBeVisible();
  await expect(fallback.getByRole('status')).toContainText('ARTIFACT_LICENSE_FEATURE_DISABLED');
  await expect(fallback).toContainText('Editing, paste, save, and AI apply are disabled.');
  const cellCount = await page.evaluate(() => {
    const state = (window as unknown as {
      __structuredArtifactE2eState: {
        snapshot(): { content: { sheets: Array<{ cells: Record<string, unknown> }> } };
      };
    }).__structuredArtifactE2eState;
    return Object.keys(state.snapshot().content.sheets[0]?.cells ?? {}).length;
  });
  expect(cellCount).toBe(10_000);
  await expect(summary).toContainText('[more fields]');
  expect((await summary.textContent())?.length).toBeLessThanOrEqual(8_194);
  const beforePaste = await summary.textContent();
  await fallback.evaluate((element) => {
    const clipboard = new DataTransfer();
    clipboard.setData('text/plain', '9\t10');
    element.dispatchEvent(new ClipboardEvent('paste', {
      bubbles: true, cancelable: true, clipboardData: clipboard,
    }));
  });
  expect(await summary.textContent()).toBe(beforePaste);
  expect(await structuredArtifactCommands(page)).not.toContain('bridge_artifact_spreadsheet_patch');
  expect(await structuredArtifactCommands(page)).not.toContain('bridge_artifact_mutate');
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
  await workbench.getByRole('button', { name: 'Export XLSX' }).click();
  await expect.poll(async () => (await structuredArtifactCommands(page)).filter((item) => item.includes('export')))
    .toEqual([
      'bridge_artifact_export_begin', 'bridge_artifact_export_commit',
      'bridge_artifact_export_begin', 'bridge_artifact_export_commit',
    ]);
  expect(await structuredArtifactCommands(page)).not.toContain('bridge_artifact_mutate');
  consoleHealth.assertNoCriticalErrors();
});
