import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';

import {
  e2eArtifactPath,
  expectNoHorizontalOverflow,
  gotoOperatorPanel,
  openPrimaryView,
  readLayoutMetrics,
  saveE2eScreenshot,
} from './helpers';

type ViewportCase = {
  name: string;
  width: number;
  height: number;
};

const viewports: ViewportCase[] = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'compact-desktop', width: 1024, height: 768 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 390, height: 844 },
];

async function writeResponsiveReport(rows: Array<ViewportCase & { overflowX: number }>) {
  fs.writeFileSync(e2eArtifactPath('responsive', 'responsive-report.json'), JSON.stringify({ rows }, null, 2));
  fs.writeFileSync(
    e2eArtifactPath('responsive', 'responsive-report.md'),
    [
      '# Operator Panel Responsive Smoke',
      '',
      '| Viewport | Size | Horizontal overflow |',
      '|---|---:|---:|',
      ...rows.map((row) => `| ${row.name} | ${row.width}x${row.height} | ${row.overflowX}px |`),
      '',
    ].join('\n'),
  );
}

async function expectWorkspaceReady(page: Page) {
  await expect(page.getByRole('heading', { name: 'Mission Control', exact: true })).toBeVisible();
  await expect(page.locator('.mission-control-view')).toBeVisible();
}

test('viewport matrix keeps the workspace usable without horizontal overflow', async ({ page }) => {
  const rows: Array<ViewportCase & { overflowX: number }> = [];

  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });
    await expectWorkspaceReady(page);
    const metrics = await expectNoHorizontalOverflow(page, viewport.name);
    rows.push({ ...viewport, overflowX: metrics.overflowX });
    await saveE2eScreenshot(page, `workspace-${viewport.name}`);

    if (viewport.name === 'desktop') {
      await expect(page.locator('.context-rail')).toBeVisible();
    }

    if (viewport.name === 'mobile') {
      await page.getByRole('button', { name: 'Menü', exact: true }).click();
      await expect(page.getByRole('navigation', { name: 'Ana navigasyon' })).toBeVisible();
      await page.getByRole('navigation', { name: 'Ana navigasyon' }).getByRole('button', { name: 'Görevler', exact: true }).click();
      await expect(page.getByRole('heading', { name: 'Tasks', exact: true })).toBeVisible();
      await expectNoHorizontalOverflow(page, 'mobile tasks');
    }

    consoleHealth.assertNoCriticalErrors();
  }

  await writeResponsiveReport(rows);
});

test('desktop primary views render screenshots and stay within viewport width', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });
  const views = [
    { nav: 'Görevler', heading: 'Tasks', screenshot: 'tasks-desktop' },
    { nav: 'Onaylar', heading: 'Approvals', screenshot: 'approvals-desktop' },
    { nav: 'Çalıştırmalar', heading: 'Runs', screenshot: 'runs-desktop' },
    { nav: 'Sistem Sağlığı', heading: 'System', screenshot: 'system-desktop' },
    { nav: 'Yürütmeler', heading: 'Operations', screenshot: 'operations-desktop' },
    { nav: 'Ayarlar', heading: 'Settings', screenshot: 'settings-desktop' },
  ];

  await saveE2eScreenshot(page, 'workspace-desktop');
  await expectNoHorizontalOverflow(page, 'workspace desktop');

  for (const view of views) {
    await openPrimaryView(page, view.nav, view.heading);
    await expectNoHorizontalOverflow(page, view.screenshot);
    await saveE2eScreenshot(page, view.screenshot);
  }

  const finalMetrics = await readLayoutMetrics(page);
  expect(finalMetrics.viewportWidth).toBe(1440);
  consoleHealth.assertNoCriticalErrors();
});
