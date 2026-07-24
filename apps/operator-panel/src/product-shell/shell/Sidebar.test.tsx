import { screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const workspace = vi.hoisted(() => ({
  listProjects: vi.fn(), listTasks: vi.fn(), updateProject: vi.fn(), archiveProject: vi.fn(), registerProjectFromFolder: vi.fn(),
}));

vi.mock('../adapters/productWorkspaceClient', () => ({ productWorkspaceClient: workspace }));
vi.mock('./GlobalSearch', () => ({ GlobalSearch: () => <div /> }));

import { renderOperatorPanel } from '../../test/render';
import { Sidebar } from './Sidebar';

const project = {
  projectId: 'project-release', workspaceId: 'workspace-1', title: 'Release workspace',
  rootRef: 'root-release', rootDisplayName: 'Release workspace', status: 'active' as const,
  pinned: false, manualOrder: 2, createdAtUtc: '2026-07-24T12:00:00Z', updatedAtUtc: '2026-07-24T12:00:00Z', archivedAtUtc: null,
};

describe('Sidebar project lifecycle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    workspace.listProjects.mockResolvedValue({ projects: [project], nextCursor: null });
    workspace.listTasks.mockResolvedValue({ tasks: [] });
    workspace.updateProject.mockResolvedValue({ ...project, pinned: true });
  });

  it('renders durable projects and persists a pin action through the workspace client', async () => {
    const { user } = renderOperatorPanel(<MemoryRouter><Sidebar /></MemoryRouter>);

    await user.click(await screen.findByRole('button', { name: 'Pin Release workspace' }));

    await waitFor(() => expect(workspace.updateProject).toHaveBeenCalledWith('project-release', { pinned: true }));
  });
});
