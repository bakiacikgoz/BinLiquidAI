import { screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const workspace = vi.hoisted(() => ({
  listProjects: vi.fn(),
  getOrCreateProject: vi.fn(),
  createTask: vi.fn(),
  addMessage: vi.fn(),
}));
const navigate = vi.hoisted(() => vi.fn());

vi.mock('../adapters/productWorkspaceClient', () => ({ productWorkspaceClient: workspace }));
vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal<typeof import('react-router-dom')>()),
  useNavigate: () => navigate,
}));

import { renderOperatorPanel } from '../../test/render';
import { NewWorkPage } from './NewWorkPage';

const existingProject = {
  projectId: 'project-existing', workspaceId: 'workspace-1', title: 'Release work', status: 'active',
  createdAtUtc: '2026-07-24T12:00:00Z', updatedAtUtc: '2026-07-24T12:00:00Z',
};

describe('NewWorkPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    workspace.listProjects.mockResolvedValue({ projects: [existingProject] });
    workspace.createTask.mockResolvedValue({
      taskId: 'task-1', title: 'Prepare a release', status: 'active', assistantSessionId: 'session-1',
      createdAtUtc: '2026-07-24T12:01:00Z', updatedAtUtc: '2026-07-24T12:01:00Z',
    });
    workspace.addMessage.mockResolvedValue({ messageId: 'message-1' });
  });

  it('creates work in the project the user selected', async () => {
    const { user } = renderOperatorPanel(<MemoryRouter><NewWorkPage /></MemoryRouter>);

    await screen.findByRole('option', { name: 'Release work' });
    await user.selectOptions(screen.getByRole('combobox', { name: 'Project' }), 'project-existing');
    await user.type(screen.getByRole('textbox', { name: 'Message ImperaOS' }), 'Prepare a release');
    await user.click(screen.getByRole('button', { name: 'Send' }));

    expect(workspace.createTask).toHaveBeenCalledWith('project-existing', 'Prepare a release', expect.stringMatching(/^product-session-/));
    expect(workspace.addMessage).toHaveBeenCalledWith('task-1', 'user', 'Prepare a release');
    expect(workspace.getOrCreateProject).not.toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith('/task/task-1', { state: { initialMessage: 'Prepare a release' } });
  });
});
