import { expect, test } from '@playwright/test';

for (const viewport of [{ width: 1280, height: 800 }, { width: 900, height: 600 }, { width: 375, height: 667 }]) {
  test(`model settings remain opaque and reachable at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto('/');
    const trigger = page.locator('.composer-model');
    await trigger.click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    const layout = await dialog.evaluate((element) => {
      const rect = element.getBoundingClientRect();
      return { background: getComputedStyle(element).backgroundColor, top: rect.top, left: rect.left, right: rect.right, bottom: rect.bottom };
    });
    expect(layout.background).not.toBe('rgba(0, 0, 0, 0)');
    expect(layout.top).toBeGreaterThanOrEqual(0);
    expect(layout.left).toBeGreaterThanOrEqual(0);
    expect(layout.right).toBeLessThanOrEqual(viewport.width);
    expect(layout.bottom).toBeLessThanOrEqual(viewport.height);
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await expect(trigger).toBeFocused();
    await trigger.click();
    await page.mouse.click(5, 5);
    await expect(dialog).toHaveCount(0);
  });
}
