import { expect, test } from '@playwright/test';
import fs from 'node:fs';

import { routeGroups } from '../src/routeRegistry';
import { e2eArtifactPath, gotoOperatorPanel } from './helpers';

const visibleRoutes = routeGroups.flatMap((group) => group.routes);
const blockedPlaceholderPhrases = [
  'No evidence pack selected',
  'coming soon',
  'todo',
  'placeholder',
];

test('all visible navigation items render productized pages without aliases', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });
  const visitedHeadings = new Set<string>();
  const manifestRows: Array<{
    routeId: string;
    nav: string;
    heading: string;
    screenshot: string;
    renderMs: number;
  }> = [];

  for (const route of visibleRoutes) {
    const startedAt = performance.now();
    const nav = page.getByRole('navigation', { name: 'Ana navigasyon' });
    await nav.getByRole('button', { name: route.label, exact: true }).click();

    await expect(page.getByTestId('page-primary-region')).toBeVisible();
    await expect(page.locator('body')).toContainText(route.heading);
    const renderMs = Math.round(performance.now() - startedAt);

    const primaryText = await page.getByTestId('page-primary-region').innerText();
    expect(primaryText.trim().length, `${route.label} primary region should not be empty`).toBeGreaterThan(80);
    for (const phrase of blockedPlaceholderPhrases) {
      expect(primaryText.toLowerCase()).not.toContain(phrase.toLowerCase());
    }
    expect(visitedHeadings.has(route.heading), `${route.label} heading should be unique`).toBe(false);
    visitedHeadings.add(route.heading);

    const screenshot = e2eArtifactPath('productized-pages', 'screenshots', `${route.routeId}.png`);
    await page.screenshot({ path: screenshot, fullPage: true });
    manifestRows.push({
      routeId: route.routeId,
      nav: route.label,
      heading: route.heading,
      screenshot,
      renderMs,
    });
  }

  consoleHealth.assertNoCriticalErrors();
  fs.writeFileSync(
    e2eArtifactPath('productized-pages', 'manifest.json'),
    JSON.stringify(
      {
        generatedAtUtc: new Date().toISOString(),
        aliasViews: [],
        consoleMessages: consoleHealth.errors,
        pageErrors: [],
        pages: manifestRows,
      },
      null,
      2,
    ),
  );
});
