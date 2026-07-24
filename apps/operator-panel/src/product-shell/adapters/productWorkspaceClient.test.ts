import { beforeEach, describe, expect, it, vi } from 'vitest';

const invoke = vi.hoisted(() => vi.fn());

vi.mock('@tauri-apps/api/core', () => ({ invoke }));

import { ProductWorkspaceClient } from './productWorkspaceClient';

const activeProject = {
  projectId: 'project-operator',
  workspaceId: 'workspace-1',
  title: 'Operator work',
  status: 'active',
  createdAtUtc: '2026-07-24T12:00:00Z',
  updatedAtUtc: '2026-07-24T12:00:00Z',
};

function success(data: unknown) {
  return { ok: true as const, data, error: null };
}

describe('ProductWorkspaceClient default projects', () => {
  beforeEach(() => vi.clearAllMocks());

  it('reuses the existing active operator project for new work', async () => {
    invoke.mockResolvedValueOnce(success({ projects: [activeProject] }));

    await expect(new ProductWorkspaceClient().getOrCreateProject('Operator work')).resolves.toMatchObject(activeProject);

    expect(invoke).toHaveBeenCalledTimes(1);
    expect(invoke).toHaveBeenLastCalledWith('bridge_product_project_list', expect.anything());
  });

  it('creates a project only when no active project has that title', async () => {
    invoke
      .mockResolvedValueOnce(success({ projects: [{ ...activeProject, status: 'archived' }] }))
      .mockResolvedValueOnce(success(activeProject));

    await expect(new ProductWorkspaceClient().getOrCreateProject('Operator work')).resolves.toMatchObject(activeProject);

    expect(invoke).toHaveBeenCalledTimes(2);
    expect(invoke).toHaveBeenLastCalledWith('bridge_product_project_create', expect.objectContaining({
      payload: expect.objectContaining({ params: expect.objectContaining({ title: 'Operator work' }) }),
    }));
  });

  it('sends durable project pin and ordering changes through the governed bridge', async () => {
    invoke.mockResolvedValueOnce(success({ ...activeProject, pinned: true, manualOrder: 3 }));

    await expect(new ProductWorkspaceClient().updateProject('project-operator', {
      pinned: true,
      manualOrder: 3,
    })).resolves.toMatchObject({ projectId: 'project-operator', pinned: true, manualOrder: 3 });

    expect(invoke).toHaveBeenCalledWith('bridge_product_project_update', expect.objectContaining({
      payload: expect.objectContaining({
        params: expect.objectContaining({ projectId: 'project-operator', pinned: true, manualOrder: 3 }),
        idempotencyKey: expect.stringMatching(/^project-update-/),
      }),
    }));
  });

  it('uses the native picker ticket without exposing a local filesystem path', async () => {
    invoke
      .mockResolvedValueOnce(success({ cancelled: false, folderTicket: 'folder-opaque-1', displayName: 'Release workspace' }))
      .mockResolvedValueOnce(success(activeProject));

    await expect(new ProductWorkspaceClient().registerProjectFromFolder()).resolves.toMatchObject(activeProject);

    expect(invoke).toHaveBeenLastCalledWith('bridge_product_project_register', {
      request: expect.objectContaining({ folderTicket: 'folder-opaque-1', name: 'Release workspace', idempotencyKey: expect.stringMatching(/^project-register-/) }),
    });
  });
});
