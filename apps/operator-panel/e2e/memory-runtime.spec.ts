import { expect, test } from '@playwright/test';

import { gotoOperatorPanel, openPrimaryView } from './helpers';

test('memory runtime page renders runtime evidence without raw content', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });

  await openPrimaryView(page, 'Memory Runtime', 'Memory Runtime');

  const region = page.getByTestId('page-primary-region');
  await expect(region.getByTestId('memory-runtime-evidence')).toContainText('Runtime bridge');
  await expect(region).toContainText('Sync pack');
  await expect(region).not.toContainText('rawContent');

  consoleHealth.assertNoCriticalErrors();
});
