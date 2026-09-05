import { expect, test } from '@playwright/test';

test('new project stays on one row and conversation hover shows its information', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  // Isolated presentation fixture: no native workspace mutations.
  await page.addInitScript(() => {
    localStorage.setItem('imperaos-product-shell-preferences-v2', JSON.stringify({ state: { sidebarCollapsed: false, sidebarWidth: 270 }, version: 0 }));
    const base = { workspaceId: 'visual-fixture', status: 'active', pinned: false, manualOrder: 0, createdAtUtc: '2026-09-05T08:00:00Z', updatedAtUtc: '2026-09-05T08:00:00Z', archivedAtUtc: null };
    const existing = { ...base, projectId: 'existing', title: 'ImperaOs', rootRef: 'root-existing', rootDisplayName: 'Workspace / ImperaOs' };
    const added = { ...base, projectId: 'added', title: 'Yeni klasör (2)', rootRef: 'root-added', rootDisplayName: 'Yeni klasör (2)' };
    let registered = false;
    const task = { ...base, taskId: 'conversation', projectId: 'existing', title: 'Projeyi güncelle', priority: 0, reasoningEffort: 'medium', speedProfile: 'standard', approvalProfile: 'risk_based', assistantSessionId: null, assistantTurnId: null, teamJobId: null };
    Object.defineProperty(window, '__TAURI_INTERNALS__', { value: {
      invoke: async (command: string, args: { payload?: { params?: { projectId?: string } } }) => {
        let data: unknown;
        if (command === 'bridge_product_project_list') data = { projects: registered ? [added, existing] : [existing], nextCursor: null };
        else if (command === 'bridge_product_task_list') data = { tasks: args.payload?.params?.projectId === 'existing' ? [task] : [] };
        else if (command === 'bridge_product_project_folder_select') data = { cancelled: false, folderTicket: 'fixture-ticket', displayName: added.title };
        else if (command === 'bridge_product_project_register') { registered = true; data = added; }
        else throw new Error('Unavailable in isolated visual fixture');
        return { ok: true, data, error: null };
      },
    } });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Yeni proje', exact: true }).click();
  await expect(page.getByText('Sohbet yok', { exact: true })).toBeVisible();
  const row = page.locator('.project-header-row').filter({ has: page.getByRole('button', { name: 'Yeni klasör (2)', exact: true }) });
  await row.hover();
  const bounds = await row.evaluate((element) => {
    const row = element.getBoundingClientRect();
    const action = element.querySelector('.project-create-task')!.getBoundingClientRect();
    return { height: row.height, contained: action.top >= row.top && action.bottom <= row.bottom && action.right <= row.right };
  });
  expect(bounds.height).toBe(34);
  expect(bounds.contained).toBe(true);
  await expect(page.locator('.codex-sidebar')).toHaveCSS('background-color', 'rgb(32, 32, 32)');
  await page.locator('.project-task').first().hover();
  const tooltip = page.getByRole('tooltip');
  await expect(tooltip).toBeVisible();
  await expect(tooltip).toContainText('ImperaOs');
  await expect(tooltip).toContainText('1 sohbet');
  await page.keyboard.press('Escape');
  await expect(tooltip).toHaveCount(0);
  await page.getByRole('button', { name: 'Görevleri düzenle' }).click();
  await page.getByText('Filtrele ve yenile').click();
  await page.getByLabel('Görevlerde ara').fill('eşleşmeyen görev');
  await expect(page.locator('.recent-list a')).toHaveCount(0);
  await page.getByLabel('Görevlerde ara').clear();
  await expect(page.locator('.recent-list a')).toHaveText('Projeyi güncelle');
  await page.getByRole('button', { name: 'Görevleri düzenle' }).click();
  await page.getByRole('button', { name: 'Yakın zamanlılar', exact: true }).click();
  await expect(page.locator('.recent-list')).toHaveCount(0);
  await page.getByRole('button', { name: 'Yakın zamanlılar', exact: true }).click();
  await expect(page.locator('.recent-list a')).toBeVisible();
  await page.locator('textarea').fill('Eski sohbet taslağı');
  await page.getByRole('button', { name: 'Yeni sohbet', exact: true }).click();
  await expect(page.locator('textarea')).toHaveValue('');
  await expect(page.getByRole('button', { name: 'Project', exact: true })).toHaveText('Proje seç');
  await expect(page.locator('.composer-context-bar')).not.toContainText('Branch');
  await expect(page.locator('.composer-context-bar')).not.toContainText('Yerel');
  await page.getByRole('button', { name: 'Project', exact: true }).click();
  await page.getByRole('textbox', { name: 'Proje ara' }).fill('impera');
  await expect(page.getByRole('option')).toHaveCount(1);
  await page.screenshot({ path: test.info().outputPath('compact-project-picker.png') });
  await page.getByRole('option', { name: 'ImperaOs' }).click();
  await expect(page.getByRole('heading', { name: 'ImperaOs projesinde ne oluşturalım?' })).toBeVisible();
  const composer = await page.locator('.composer.codex-composer').boundingBox();
  expect(composer!.width).toBeLessThanOrEqual(736);
  expect(composer!.height).toBeLessThanOrEqual(110);

  await page.getByRole('button', { name: 'Görevleri düzenle' }).click();
  await page.getByRole('button', { name: 'Sohbetleri sıralama ölçütü' }).hover();
  await expect(page.getByRole('menuitemradio', { name: 'Son güncelleme', exact: true })).toHaveAttribute('aria-checked', 'true');
  await page.screenshot({ path: test.info().outputPath('sidebar-menu.png') });
  await page.getByRole('menuitemradio', { name: 'Öncelik', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Sohbet düzeni' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Görevleri düzenle' }).click();
  await page.getByText('Filtrele ve yenile').click();
  await page.getByLabel('Görev durumu').selectOption('completed');
  await expect(page.locator('.recent-list')).toContainText('Bu filtreye uygun görev yok.');
  await page.getByLabel('Görev durumu').selectOption('all');
  await page.getByRole('button', { name: 'Görevleri yenile' }).click();
  await expect(page.locator('.recent-list a')).toHaveText('Projeyi güncelle');
});
