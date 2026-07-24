import { screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const navigate = vi.hoisted(() => vi.fn());
const workspace = vi.hoisted(() => ({ listProjects: vi.fn(), listTasks: vi.fn() }));
const artifactBridge = vi.hoisted(() => ({ list: vi.fn() }));
const bridge = vi.hoisted(() => ({ fetchApprovals: vi.fn(), listControlPlaneAgents: vi.fn() }));

vi.mock('../adapters/productWorkspaceClient', () => ({ productWorkspaceClient: workspace }));
vi.mock('../../artifact-workspace/artifactBridge', () => ({ artifactBridge }));
vi.mock('../../bridge', () => bridge);
vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal<typeof import('react-router-dom')>()),
  useNavigate: () => navigate,
}));

import { renderOperatorPanel } from '../../test/render';
import { GlobalSearch } from './GlobalSearch';

describe('GlobalSearch', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    workspace.listProjects.mockResolvedValue({ projects: [{
      projectId: 'project-1', workspaceId: 'workspace-1', title: 'Release', status: 'active',
      createdAtUtc: '2026-07-24T12:00:00Z', updatedAtUtc: '2026-07-24T12:00:00Z',
    }] });
    workspace.listTasks.mockResolvedValue({ tasks: [{
      taskId: 'task-1', workspaceId: 'workspace-1', projectId: 'project-1', title: 'Quarterly release plan', status: 'active',
      assistantSessionId: null, assistantTurnId: null, teamJobId: null, createdAtUtc: '2026-07-24T12:00:00Z', updatedAtUtc: '2026-07-24T12:00:00Z',
    }] });
    artifactBridge.list.mockResolvedValue({ items: [], nextCursor: null });
    bridge.fetchApprovals.mockResolvedValue({ pending: [] });
    bridge.listControlPlaneAgents.mockResolvedValue({ agents: [] });
  });

  it('opens a matching durable task route', async () => {
    const { user } = renderOperatorPanel(<MemoryRouter><GlobalSearch /></MemoryRouter>);

    await user.type(screen.getByRole('textbox', { name: 'Search' }), 'quarterly');
    const result = await screen.findByRole('button', { name: /Quarterly release plan/ });
    await user.click(result);

    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/task/task-1'));
  });
});
