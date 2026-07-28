import { expect, test } from '@playwright/test';

const viewports = [
  { width: 1440, height: 900 },
  { width: 1280, height: 800 },
  { width: 1024, height: 768 },
  { width: 768, height: 900 },
  { width: 390, height: 844 },
];

test('product home preserves the UI Lab hierarchy and responsive bounds', async ({ page }) => {
  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await page.goto('/#/', { waitUntil: 'networkidle' });
    await expect(page.locator('style[data-ui-lab-theme]')).toHaveCount(1);
    await expect(page.locator('.app-shell.has-closed-panels')).toBeVisible();
    await expect(page.locator('.new-work-page.codex-home')).toBeVisible();
    await expect(page.locator('.suggestion-grid.codex-suggestions')).toBeVisible();
    await expect(page.locator('.composer-stack.is-home')).toBeVisible();
    await expect(page.locator('.composer.codex-composer')).toBeVisible();
    const overflow = await page.evaluate(() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth));
    expect(overflow).toBeLessThanOrEqual(2);
  }
});

test('collection, settings and search surfaces use the UI Lab contracts', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/#/library', { waitUntil: 'networkidle' });
  await expect(page.locator('.collection-page .collection-list')).toBeVisible();

  await page.goto('/#/settings', { waitUntil: 'networkidle' });
  await expect(page.locator('.settings-shell .settings-sidebar')).toBeVisible();
  await expect(page.locator('.settings-content .settings-page')).toBeVisible();

  await page.goto('/#/', { waitUntil: 'networkidle' });
  await page.keyboard.press(process.platform === 'darwin' ? 'Meta+K' : 'Control+K');
  await expect(page.locator('.modal-backdrop .search-modal')).toBeVisible();
});

test('product adapter styles are removed during a real route transition into the legacy shell', async ({ page }) => {
  await page.goto('/#/', { waitUntil: 'networkidle' });
  await expect(page.locator('style[data-product-shell-adapters]')).toHaveCount(1);
  expect(await page.evaluate(() => {
    const probe = document.createElement('div');
    probe.className = 'native-terminal-surface';
    document.body.append(probe);
    return getComputedStyle(probe).display;
  })).toBe('flex');

  await page.goto('/#/system/settings', { waitUntil: 'networkidle' });
  await expect(page.locator('style[data-ui-lab-theme]')).toHaveCount(0);
  await expect(page.locator('style[data-product-shell-adapters]')).toHaveCount(0);
  expect(await page.evaluate(() => {
    const probe = document.createElement('div');
    probe.className = 'native-terminal-surface';
    document.body.append(probe);
    return getComputedStyle(probe).display;
  })).toBe('block');
});
