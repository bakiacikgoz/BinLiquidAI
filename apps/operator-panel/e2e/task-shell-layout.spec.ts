import { expect, test } from '@playwright/test';

test('full task shell centers the conversation and exposes its environment controls', async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1000 });
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
        else if (command === 'bridge_product_task_get') data = task;
        else if (command === 'bridge_product_task_message_list') data = { messages: [{messageId:'m1',workspaceId:'visual-fixture',taskId:'conversation',role:'user',body:'merhaba',createdAtUtc:base.createdAtUtc}] };
        else if (command === 'bridge_product_task_link_list') data = { links: [] };
        else throw new Error('Unavailable in isolated visual fixture');
        return { ok: true, data, error: null };
      },
    } });
  });
  await page.goto('/#/task/conversation');
  await expect(page.locator('.task-crumb')).toHaveText('Projeyi güncelle');
  await expect(page.locator('.user-message')).toHaveText('merhaba');
  const verifyCenter = async () => {
    const pane = await page.locator('.conversation-pane').boundingBox();
    const composer = await page.locator('.composer-stack').boundingBox();
    expect(Math.abs((composer!.x + composer!.width / 2) - (pane!.x + pane!.width / 2))).toBeLessThan(2);
    expect(composer!.width).toBe(736);
    const layout = await page.locator('.task-layout').boundingBox();
    expect(pane!.width).toBeLessThanOrEqual(layout!.width);
  };
  await verifyCenter();
  await page.getByTitle('Sabitlenmiş özeti aç/kapat', {exact:true}).click();
  await expect(page.getByRole('complementary', {name:'Task context'})).toBeVisible();
  await verifyCenter();
  const rail = await page.getByRole('complementary', {name:'Task context'}).boundingBox();
  expect(rail!.height).toBeLessThan(400);
  await page.screenshot({path:test.info().outputPath('task-shell.png')});
  await page.getByTitle('Paneli kapat').click();
  await expect(page.getByRole('complementary', {name:'Task context'})).toHaveCount(0);
  await verifyCenter();
  await page.getByTitle('Sabitlenmiş özeti aç/kapat', {exact:true}).click();
  await page.getByTitle('Çalışma alanı',{exact:true}).click();
  await expect(page.getByLabel('Çalışma alanı seç')).toBeVisible();
  await expect(page.getByRole('complementary', {name:'Task context'})).toBeVisible();
  const split = await page.locator('.split-resize').boundingBox();
  const before = await page.locator('.work-surface').boundingBox();
  await page.mouse.move(split!.x + split!.width / 2, split!.y + 180);
  await page.mouse.down();
  await page.mouse.move(split!.x - 140, split!.y + 180, {steps:8});
  await page.mouse.up();
  const after = await page.locator('.work-surface').boundingBox();
  expect(after!.width - before!.width).toBeGreaterThan(120);
  await expect(page.getByRole('complementary', {name:'Task context'})).toBeHidden();
  const group = await page.locator('.conversation-group').boundingBox();
  const reclaimed = await page.locator('.conversation-pane').boundingBox();
  expect(Math.abs(group!.width - reclaimed!.width)).toBeLessThan(2);
  const movedSplit = await page.locator('.split-resize').boundingBox();
  await page.mouse.move(movedSplit!.x, movedSplit!.y + 180);
  await page.mouse.down();
  await page.mouse.move(split!.x + split!.width / 2, split!.y + 180, {steps:8});
  await page.mouse.up();
  await expect(page.getByRole('complementary', {name:'Task context'})).toBeVisible();

  await page.setViewportSize({width:1400,height:900});
  await expect(page.getByRole('complementary', {name:'Task context'})).toBeHidden();
  await page.setViewportSize({width:1920,height:1000});
  await expect(page.getByRole('complementary', {name:'Task context'})).toBeVisible();

  await page.getByLabel('Çalışma alanı seç').getByRole('button',{name:'İncele',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Çıktılara erişilemiyor'})).toBeVisible();
  await page.screenshot({path:test.info().outputPath('compact-inspect.png')});
  await page.getByRole('button',{name:'New workspace tab'}).click();
  await page.getByRole('menuitem',{name:/Files/}).click();
  await expect(page.getByRole('tab',{name:'Files',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'New workspace tab'}).click();
  await page.getByRole('menuitem',{name:/Browser/}).click();
  await expect(page.getByText('Göz atmaya başlayın')).toBeVisible();
  await page.getByRole('button',{name:'New workspace tab'}).click();
  await page.getByRole('menuitem',{name:/Terminal/}).click();
  const terminal = page.locator('.workspace-runtime-surface:not([hidden]) .native-terminal-surface');
  await expect(terminal).toBeVisible();
  await expect(terminal.locator('header')).toBeHidden();
  await expect(terminal.locator(':scope > .ps-muted')).toBeHidden();
  await expect(terminal).toHaveCSS('background-color','rgb(24, 24, 24)');
  await expect(page.getByRole('tab', {name:'Workspace / ImperaOs',exact:true})).toBeVisible();
  await terminal.locator('.xterm-rows').evaluate((rows) => { const span = document.createElement('span'); span.dataset.testColor='true'; span.style.color='rgb(0, 120, 255)'; span.textContent='PS'; rows.appendChild(span); });
  await expect(terminal.locator('[data-test-color]')).toHaveCSS('color','rgb(230, 230, 230)');

  await page.getByRole('tab',{name:'Browser',exact:true}).click();

  await page.getByTitle('Terminal paneli',{exact:true}).click();
  await page.screenshot({path:test.info().outputPath('all-panels-browser.png')});
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
  await page.getByTitle('Terminal paneli',{exact:true}).click();

  await page.getByTitle('Çalışma alanı',{exact:true}).click();
  await page.getByTitle('Terminal paneli',{exact:true}).click();
  await expect(page.getByRole('tab',{name:'Workspace / ImperaOs',exact:true}).last()).toBeVisible();
  await page.getByRole('button',{name:'Yeni terminal',exact:true}).click();
  await expect(page.getByRole('tab',{name:'Workspace / ImperaOs',exact:true}).last()).toBeVisible();
  await page.getByRole('button',{name:'Sohbet seçenekleri',exact:true}).click();
  await expect(page.getByRole('menuitem',{name:'Yeniden adlandır'})).toBeVisible();
  await page.screenshot({path:test.info().outputPath('panels-and-menu.png')});

});
