import { screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const workspace = vi.hoisted(() => ({
  listProjects: vi.fn(),
  getOrCreateProject: vi.fn(),
  registerProjectFromFolder: vi.fn(),
  createTask: vi.fn(),
  addMessage: vi.fn(),
}));
const navigate = vi.hoisted(() => vi.fn());

vi.mock('../adapters/productWorkspaceClient', () => ({ productWorkspaceClient: workspace }));
vi.mock('../../components/assistant/AssistantComposer', () => ({
  AssistantComposer: ({
    onSend,
    projectControl,
    variant,
  }: {
    onSend: (message: string, settings: unknown, controls: unknown) => void;
    projectControl?: React.ReactNode;
    variant?: string;
  }) => (
    <div data-testid="assistant-composer" data-variant={variant}>
      {projectControl}
      <button type="button" onClick={() => onSend('Prepare a release', {
        assistantProvider: 'ollama', assistantFallbackProvider: '', assistantModel: 'qwen3.5:4b', assistantHfModelId: '',
      }, { contextAttachmentKinds: ['artifact_summary'], toolIntents: ['inspect_run'] })}>Submit composed work</button>
    </div>
  ),
}));
vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal<typeof import('react-router-dom')>()),
  useNavigate: () => navigate,
}));

import { renderOperatorPanel } from '../../test/render';
import { useProductShellStore } from '../state/productShellStore';
import { NewWorkPage } from './NewWorkPage';

const existingProject = {
  projectId: 'project-existing', workspaceId: 'workspace-1', title: 'Release work', status: 'active',
  createdAtUtc: '2026-07-24T12:00:00Z', updatedAtUtc: '2026-07-24T12:00:00Z',
};

describe('NewWorkPage', () => {
  it('retries the initial message on the already created task after persistence failure', async () => {
    workspace.addMessage.mockRejectedValueOnce(new Error('Message storage unavailable')).mockResolvedValue({ messageId: 'message-1' });
    const { user } = renderOperatorPanel(<MemoryRouter><NewWorkPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByRole('button', { name: 'Project' })).toBeEnabled());
    await user.click(screen.getByRole('button', { name: 'Project' }));
    await user.click(screen.getByRole('option', { name: 'Release work' }));
    await user.click(screen.getByRole('button', { name: 'Submit composed work' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Message storage unavailable');
    await user.click(screen.getByRole('button', { name: 'Submit composed work' }));
    expect(workspace.createTask).toHaveBeenCalledOnce();
    expect(workspace.addMessage).toHaveBeenNthCalledWith(1, 'task-1', 'user', 'Prepare a release');
    expect(workspace.addMessage).toHaveBeenNthCalledWith(2, 'task-1', 'user', 'Prepare a release');
    expect(navigate).toHaveBeenCalledWith('/task/task-1', expect.any(Object));
  });

  it('recovers a failed project load through retry without offering a fake project', async () => {
    workspace.listProjects.mockRejectedValueOnce(new Error('Desktop runtime disconnected'));
    const { user } = renderOperatorPanel(<MemoryRouter><NewWorkPage /></MemoryRouter>);
    expect(await screen.findByRole('alert')).toHaveTextContent('Projeler yüklenemedi');
    expect(screen.getByRole('alert').closest('.welcome-composer')).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Bildirimi küçült' }));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Bağlantı uyarısı' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Projeler yüklenemedi');
    expect(screen.getByRole('button', { name: 'Project' })).toBeDisabled();
    expect(screen.queryByRole('option', { name: 'Yeni “Operator work” projesi oluştur' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Projeleri yeniden yükle' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Project' })).toBeEnabled());
    await user.click(screen.getByRole('button', { name: 'Project' }));
    await user.click(screen.getByRole('option', { name: 'Release work' }));
    expect(screen.getByRole('button', { name: 'Project' })).toBeEnabled();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Submit composed work' }));
    expect(workspace.createTask).toHaveBeenCalledWith('project-existing', expect.any(String), expect.any(String), expect.any(Object));
  });

  beforeEach(() => {
    vi.clearAllMocks();
    useProductShellStore.setState({ tasks: [], selectedTaskId: null });
    workspace.listProjects.mockResolvedValue({ projects: [existingProject] });
    workspace.createTask.mockImplementation(async (projectId, _title, assistantSessionId) => ({
      taskId: 'task-1', projectId, title: 'Prepare a release', status: 'active', assistantSessionId,
      createdAtUtc: '2026-07-24T12:01:00Z', updatedAtUtc: '2026-07-24T12:01:00Z',
    }));
    workspace.addMessage.mockResolvedValue({ messageId: 'message-1' });
  });

  it('creates work in the project the user selected', async () => {
    const { user } = renderOperatorPanel(<MemoryRouter><NewWorkPage /></MemoryRouter>);

    expect(document.querySelector('.new-work-page.codex-home')).toBeInTheDocument();
    expect(document.querySelector('.suggestion-grid.codex-suggestions')).toBeInTheDocument();
    expect(screen.getByTestId('assistant-composer')).toHaveAttribute('data-variant', 'product');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Project' })).toBeEnabled());
    await user.click(screen.getByRole('button', { name: 'Project' }));
    await user.click(screen.getByRole('option', { name: 'Release work' }));
    await user.click(screen.getByRole('button', { name: 'Submit composed work' }));

    expect(workspace.createTask).toHaveBeenCalledWith('project-existing', 'Prepare a release', expect.stringMatching(/^product-session-/), {
      reasoningEffort: 'medium', speedProfile: 'standard', approvalProfile: 'risk_based',
    });
    expect(workspace.addMessage).toHaveBeenCalledWith('task-1', 'user', 'Prepare a release');
    expect(workspace.getOrCreateProject).not.toHaveBeenCalled();
    const persistedSessionId = workspace.createTask.mock.calls[0][2];
    expect(useProductShellStore.getState().tasks).toContainEqual(
      expect.objectContaining({ id: 'task-1', assistantSessionId: persistedSessionId }),
    );
    expect(navigate).toHaveBeenCalledWith('/task/task-1', {
      state: expect.objectContaining({
        initialMessage: 'Prepare a release',
        runtimeSettings: expect.objectContaining({ assistantProvider: 'ollama', assistantModel: 'qwen3.5:4b' }),
        controls: { contextAttachmentKinds: ['artifact_summary'], toolIntents: ['inspect_run'] },
      }),
    });
  });

  it('requires selection and registers a folder through the compact picker', async () => {
    workspace.listProjects.mockResolvedValue({ projects: [] });
    workspace.registerProjectFromFolder.mockResolvedValue({ ...existingProject, projectId: 'project-created' });
    const { user } = renderOperatorPanel(<MemoryRouter><NewWorkPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByRole('button', { name: 'Project' })).toBeEnabled());
    expect(screen.getByRole('button', { name: 'Project' })).toHaveTextContent('Proje seç');
    await user.click(screen.getByRole('button', { name: 'Submit composed work' }));
    expect(workspace.createTask).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Project' }));
    await user.click(screen.getByRole('button', { name: 'Yeni proje' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Project' })).toHaveTextContent('Release work'));
    await user.click(screen.getByRole('button', { name: 'Submit composed work' }));
    expect(workspace.registerProjectFromFolder).toHaveBeenCalledOnce();
    expect(workspace.createTask).toHaveBeenCalledWith('project-created', expect.any(String), expect.any(String), expect.any(Object));
  });

  it('honors a sidebar project selection beyond the first project page', async () => {
    workspace.listProjects.mockResolvedValueOnce({ projects: [existingProject], nextCursor: 'page-2' });
    workspace.listProjects.mockResolvedValueOnce({
      projects: [{ ...existingProject, projectId: 'project-later', title: 'Later project' }], nextCursor: null,
    });
    const { user } = renderOperatorPanel(<MemoryRouter initialEntries={['/?project=project-later']}><NewWorkPage /></MemoryRouter>);

    await waitFor(() => expect(screen.getByRole('button', { name: 'Project' })).toHaveTextContent('Later project'));
    await user.click(screen.getByRole('button', { name: 'Submit composed work' }));
    expect(workspace.createTask).toHaveBeenCalledWith('project-later', expect.any(String), expect.any(String), expect.any(Object));
  });

  it('does not silently create work in another project when the requested project is unavailable', async () => {
    const { user } = renderOperatorPanel(<MemoryRouter initialEntries={['/?project=missing-project']}><NewWorkPage /></MemoryRouter>);
    await waitFor(() => expect(screen.getByRole('button', { name: 'Project' })).toBeEnabled());
    await user.click(screen.getByRole('button', { name: 'Submit composed work' }));
    expect(workspace.createTask).not.toHaveBeenCalled();
    expect(await screen.findByRole('alert')).toHaveTextContent('Seçilen proje');
  });

  it('waits for project discovery before accepting a new task', async () => {
    workspace.listProjects.mockReturnValue(new Promise(() => {}));
    const { user } = renderOperatorPanel(<MemoryRouter><NewWorkPage /></MemoryRouter>);
    await user.click(screen.getByRole('button', { name: 'Submit composed work' }));
    expect(workspace.getOrCreateProject).not.toHaveBeenCalled();
    expect(workspace.createTask).not.toHaveBeenCalled();
  });

  it('stays on New Work when the initial message cannot be persisted', async () => {
    workspace.addMessage.mockRejectedValue(new Error('Initial message persistence failed.'));
    const { user } = renderOperatorPanel(<MemoryRouter><NewWorkPage /></MemoryRouter>);

    await waitFor(() => expect(screen.getByRole('button', { name: 'Project' })).toBeEnabled());
    await user.click(screen.getByRole('button', { name: 'Project' }));
    await user.click(screen.getByRole('option', { name: 'Release work' }));
    await user.click(screen.getByRole('button', { name: 'Submit composed work' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Initial message persistence failed.');
    expect(navigate).not.toHaveBeenCalled();
    expect(useProductShellStore.getState()).toMatchObject({ tasks: [], selectedTaskId: null });
  });
});
