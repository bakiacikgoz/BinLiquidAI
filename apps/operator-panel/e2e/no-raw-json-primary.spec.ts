import { expect, test } from '@playwright/test';

import { routeGroups } from '../src/routeRegistry';
import { gotoOperatorPanel } from './helpers';

const visibleRoutes = routeGroups.flatMap((group) => group.routes);

test('primary page regions do not expose raw JSON outside RawInspector', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });

  for (const route of visibleRoutes) {
    const nav = page.getByRole('navigation', { name: 'Ana navigasyon' });
    await nav.getByRole('button', { name: route.label, exact: true }).click();

    const primary = page.getByTestId('page-primary-region');
    await expect(primary).toBeVisible();

    const visiblePrimaryRawBlocks = primary.locator(
      'pre.json-panel:visible:not([data-raw-inspector-panel]), code:visible',
    );
    await expect(
      visiblePrimaryRawBlocks,
      `${route.routeId} should not show primary raw JSON/code blocks`,
    ).toHaveCount(0);

    const visibleInspectorPanels = primary.locator('[data-raw-inspector] pre:visible');
    await expect(
      visibleInspectorPanels,
      `${route.routeId} raw inspector panels should be collapsed by default`,
    ).toHaveCount(0);
  }

  consoleHealth.assertNoCriticalErrors();
});
