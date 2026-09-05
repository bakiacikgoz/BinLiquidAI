import { screen, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const assistant = vi.hoisted(() => ({
  state: {
    sessionId: 'session-task-1', turns: [] as import('../../assistant/assistantTypes').AssistantTurn[], activeTurnId: null, status: 'idle', selectedRunIds: [],
    referencedArtifacts: [], pendingApprovalId: null, error: null,
  },
  actions: {
    send: vi.fn(), newChat: vi.fn(), regenerate: vi.fn(), cancel: vi.fn(), applyEvent: vi.fn(),
    markApprovalDetailLoaded: vi.fn(), updateApprovalStatus: vi.fn(), appendSystemMessage: vi.fn(),
  },
}));
const workspace = vi.hoisted(() => ({ addLink: vi.fn(), addMessage: vi.fn(), getTask: vi.fn(), listLinks: vi.fn(), listMessages: vi.fn(), listProjects: vi.fn(), updateTask: vi.fn() }));

vi.mock('../adapters/useProductAssistant', () => ({ useProductAssistant: () => assistant }));
vi.mock('../adapters/productWorkspaceClient', () => ({ productWorkspaceClient: workspace }));
vi.mock('../workspace/WorkSurface', () => ({
  WorkSurface: ({
    onOpenArtifacts,
    onOpenTerminal,
    onOpenBrowser,
    onOpenPreview,
  }: {
    onOpenArtifacts: () => void;
    onOpenTerminal: () => void;
    onOpenBrowser: () => void;
    onOpenPreview: () => void;
  }) => <div>
    <button type="button" onClick={onOpenArtifacts}>Open artifacts</button>
    <button type="button" onClick={onOpenTerminal}>Open terminal</button>
    <button type="button" onClick={onOpenBrowser}>Open browser</button>
    <button type="button" onClick={onOpenPreview}>Open preview</button>
  </div>,
}));
vi.mock('../workspace/ProductArtifactWorkspace', () => ({ ProductArtifactWorkspace: () => null }));
vi.mock('../workspace/WorkspaceTabs', () => ({
  WorkspaceTabs: ({
    tabs,
    activeTabId,
    onOpen,
    onClose,
    projectRootRef,
  }: {
    tabs: Array<{ id: string; title: string }>;
    activeTabId: string | null;
    onOpen: (kind: 'artifacts') => void;
    onClose: (tabId: string) => void;
    projectRootRef?: string;
  }) => <div>
    <p>Workspace tabs: {tabs.map((tab) => tab.title).join(', ') || 'none'}</p>
    <p>Active workspace tab: {tabs.find((tab) => tab.id === activeTabId)?.title ?? 'none'}</p>
    <p>Terminal root: {projectRootRef ?? 'runtime-root'}</p>
    <button type="button" onClick={() => onOpen('artifacts')}>Open another artifact tab</button>
    {tabs.map((tab) => <button key={tab.id} type="button" onClick={() => onClose(tab.id)}>Close {tab.title}</button>)}
  </div>,
}));

import { renderOperatorPanel } from '../../test/render';
import { useProductShellStore } from '../state/productShellStore';
import { TaskPage } from './TaskPage';

function LocationProbe() {
  return <p>Current route: {useLocation().pathname}</p>;
}

describe('TaskPage', () => {
  it('preserves the draft when the native assistant reports startup failure', async () => {
    assistant.actions.send.mockResolvedValueOnce(false);
    const { user } = renderOperatorPanel(<MemoryRouter initialEntries={['/task/task-1']}><Routes><Route path="/task/:taskId" element={<TaskPage />} /></Routes></MemoryRouter>);
    await user.type(screen.getByRole('textbox', { name: 'Governed assistant' }), 'Keep this runtime request');
    await user.click(screen.getByRole('button', { name: 'Send' }));
    await waitFor(() => expect(assistant.actions.send).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Send' })).toBeEnabled());
    expect(screen.getByRole('textbox', { name: 'Governed assistant' })).toHaveValue('Keep this runtime request');
  });

  it('reuses the persisted user message when retrying the same failed startup', async () => {
    assistant.actions.send.mockResolvedValueOnce(false).mockResolvedValueOnce(true).mockResolvedValueOnce(true);
    const { user } = renderOperatorPanel(<MemoryRouter initialEntries={['/task/task-1']}><Routes><Route path="/task/:taskId" element={<TaskPage />} /></Routes></MemoryRouter>);
    const draft = screen.getByRole('textbox', { name: 'Governed assistant' });
    await user.type(draft, 'Retry this request');
    await user.click(screen.getByRole('button', { name: 'Send' }));
    await user.click(screen.getByRole('button', { name: 'Send' }));
    expect(assistant.actions.send).toHaveBeenCalledTimes(2);
    expect(workspace.addMessage).toHaveBeenCalledTimes(1);
    expect(draft).toHaveValue('');
    await user.type(draft, 'Retry this request');
    await user.click(screen.getByRole('button', { name: 'Send' }));
    expect(workspace.addMessage).toHaveBeenCalledTimes(2);
  });

  it('returns to the conversation after closing the final workspace tab', async () => {
    const { user } = renderOperatorPanel(<MemoryRouter initialEntries={['/task/task-1/workspace']}><LocationProbe /><Routes><Route path="/task/:taskId" element={<TaskPage />} /><Route path="/task/:taskId/workspace" element={<TaskPage />} /></Routes></MemoryRouter>);
    await user.click(screen.getByRole('button', { name: 'Open another artifact tab' }));
    await user.click(await screen.findByRole('button', { name: 'Close Artifacts' }));
    await waitFor(() => expect(screen.getByText('Current route: /task/task-1')).toBeInTheDocument());
    expect(screen.queryByText('Workspace tabs: Artifacts')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Open artifacts' })).toBeInTheDocument();
  });

  it('reports a rejected task runtime setting without pretending it was applied', async () => {
    workspace.updateTask.mockRejectedValue(new Error('Runtime update denied'));
    const { user } = renderOperatorPanel(<MemoryRouter initialEntries={['/task/task-1']}><Routes><Route path="/task/:taskId" element={<TaskPage />} /></Routes></MemoryRouter>);
    await user.click(screen.getByRole('button', { name: /profile default/i }));
    await user.selectOptions(screen.getByRole('combobox', { name: 'Reasoning effort' }), 'high');
    expect(await screen.findByRole('alert')).toHaveTextContent('Runtime update denied');
    expect(screen.getByRole('combobox', { name: 'Reasoning effort' })).toHaveValue('medium');
  });

  it('shows a persistence failure without starting an assistant turn', async () => {
    workspace.addMessage.mockRejectedValue(new Error('Message storage unavailable'));
    const { user } = renderOperatorPanel(<MemoryRouter initialEntries={['/task/task-1']}><Routes><Route path="/task/:taskId" element={<TaskPage />} /></Routes></MemoryRouter>);
    await user.type(screen.getByRole('textbox', { name: 'Governed assistant' }), 'Keep this message');
    await user.click(screen.getByRole('button', { name: 'Send' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Message storage unavailable');
    expect(assistant.actions.send).not.toHaveBeenCalled();
    expect(screen.getByRole('textbox', { name: 'Governed assistant' })).toHaveValue('Keep this message');
  });

  it('restores a cached task project after StrictMode effect replay', async () => {
    useProductShellStore.setState({
      projects: [],
      tasks: [{ id: 'task-1', projectId: 'project-1', title: 'Prepare release', createdAt: '2026-07-24T12:00:00Z', status: 'active' }],
    });
    workspace.listProjects.mockResolvedValue({
      projects: [{ projectId: 'project-1', rootRef: 'root-release', rootDisplayName: 'Release workspace', title: 'Release', status: 'active' }],
      nextCursor: null,
    });
    renderOperatorPanel(<StrictMode><MemoryRouter initialEntries={['/task/task-1']}><Routes><Route path="/task/:taskId" element={<TaskPage />} /></Routes></MemoryRouter></StrictMode>);

    expect(await screen.findByRole('heading', { name: 'Prepare release' })).toBeInTheDocument();
    expect(useProductShellStore.getState().projects).toContainEqual(expect.objectContaining({ projectId: 'project-1', rootRef: 'root-release' }));
  });

  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    workspace.addMessage.mockResolvedValue({});
    workspace.addLink.mockResolvedValue({});
    workspace.listMessages.mockResolvedValue({ messages: [] });
    workspace.listLinks.mockResolvedValue({ links: [] });
    workspace.listProjects.mockResolvedValue({ projects: [], nextCursor: null });
    workspace.updateTask.mockResolvedValue({
      taskId: 'task-1', title: 'Prepare release', status: 'active', assistantSessionId: 'session-task-1',
      reasoningEffort: 'high', speedProfile: 'standard', approvalProfile: 'risk_based',
      createdAtUtc: '2026-07-24T12:00:00Z', updatedAtUtc: '2026-07-24T12:00:00Z',
    });
    useProductShellStore.setState({
      tasks: [{ id: 'task-1', title: 'Prepare release', createdAt: '2026-07-24T12:00:00Z', status: 'active', assistantSessionId: 'session-task-1' }],
      selectedTaskId: null,
      dockOpen: false,
    });
  });

  it('sends the persisted first prompt exactly once after task navigation', async () => {
    const runtimeSettings = {
      assistantProvider: 'ollama', assistantFallbackProvider: '', assistantModel: 'qwen3.5:4b', assistantHfModelId: '',
    };
    const controls = { contextAttachmentKinds: ['artifact_summary'], toolIntents: ['inspect_run'] };
    renderOperatorPanel(<MemoryRouter initialEntries={[{ pathname: '/task/task-1', state: { initialMessage: 'Prepare a release', runtimeSettings, controls } }]}><Routes><Route path="/task/:taskId" element={<TaskPage />} /></Routes></MemoryRouter>);

    expect(document.querySelector('main.task-page .task-layout .conversation-pane')).toBeInTheDocument();
    expect(document.querySelector('.sticky-composer .composer-stack')).toBeInTheDocument();
    await waitFor(() => expect(assistant.actions.send).toHaveBeenCalledWith('Prepare a release', {
      ...runtimeSettings, reasoningEffort: 'medium', speedProfile: 'standard', approvalProfile: 'risk_based',
    }, controls));
    expect(workspace.addMessage).not.toHaveBeenCalledWith('task-1', 'user', 'Prepare a release');
  });

  it('persists a changed task reasoning profile before the next assistant turn', async () => {
    const { user } = renderOperatorPanel(<MemoryRouter initialEntries={['/task/task-1']}><Routes><Route path="/task/:taskId" element={<TaskPage />} /></Routes></MemoryRouter>);

    await user.click(screen.getByRole('button', { name: /profile default/i }));
    await user.selectOptions(await screen.findByRole('combobox', { name: 'Reasoning effort' }), 'high');

    await waitFor(() => expect(workspace.updateTask).toHaveBeenCalledWith('task-1', {
      runtime: { reasoningEffort: 'high', speedProfile: 'standard', approvalProfile: 'risk_based' },
    }));
  });

  it('hydrates a durable task on a direct task-route reload instead of redirecting', async () => {
    useProductShellStore.setState({ tasks: [], projects: [], selectedTaskId: null });
    workspace.getTask.mockResolvedValue({
      taskId: 'task-1', projectId: 'project-1', title: 'Prepare release', status: 'active',
      assistantSessionId: 'session-task-1', reasoningEffort: 'high', speedProfile: 'standard',
      approvalProfile: 'risk_based', createdAtUtc: '2026-07-24T12:00:00Z', updatedAtUtc: '2026-07-24T12:00:00Z',
    });
    workspace.listProjects.mockResolvedValue({
      projects: [{
        projectId: 'project-1', rootRef: '', rootDisplayName: '',
        title: 'Release', status: 'active',
      }],
      nextCursor: null,
    });

    renderOperatorPanel(<MemoryRouter initialEntries={['/task/task-1']}><Routes><Route path="/task/:taskId" element={<TaskPage />} /><Route path="/" element={<p>Fallback route</p>} /></Routes></MemoryRouter>);

    expect(await screen.findByRole('heading', { name: 'Prepare release' })).toBeInTheDocument();
    expect(workspace.getTask).toHaveBeenCalledWith('task-1');
    expect(screen.queryByText('Fallback route')).not.toBeInTheDocument();
  });

  it.each(['/task/task-1', '/task/task-1/workspace'])(
    'clears selection and redirects an archived task route to safe navigation: %s',
    async (route) => {
      useProductShellStore.setState({
        tasks: [{
          id: 'task-1',
          title: 'Prepare release',
          createdAt: '2026-07-24T12:00:00Z',
          status: 'archived',
          archivedAt: '2026-08-07T07:00:00Z',
        }],
        selectedTaskId: 'task-1',
      });

      renderOperatorPanel(
        <MemoryRouter initialEntries={[route]}>
          <LocationProbe />
          <Routes>
            <Route path="/task/:taskId" element={<TaskPage />} />
            <Route path="/task/:taskId/workspace" element={<TaskPage />} />
            <Route path="/" element={<p>Safe route</p>} />
          </Routes>
        </MemoryRouter>,
      );

      expect(await screen.findByText('Safe route')).toBeInTheDocument();
      expect(screen.getByText('Current route: /')).toBeInTheDocument();
      expect(useProductShellStore.getState().selectedTaskId).toBeNull();
      expect(useProductShellStore.getState().tasks).toEqual([
        expect.objectContaining({ id: 'task-1', status: 'archived' }),
      ]);
    },
  );

  it('hydrates the task project root on a direct workspace-route reload', async () => {
    useProductShellStore.setState({ tasks: [], projects: [], selectedTaskId: null });
    workspace.getTask.mockResolvedValue({
      taskId: 'task-1', projectId: 'project-1', title: 'Prepare release', status: 'active',
      assistantSessionId: 'session-task-1', reasoningEffort: 'high', speedProfile: 'standard',
      approvalProfile: 'risk_based', createdAtUtc: '2026-07-24T12:00:00Z', updatedAtUtc: '2026-07-24T12:00:00Z',
    });
    workspace.listProjects.mockResolvedValue({
      projects: [{
        projectId: 'project-1', rootRef: 'root-release', rootDisplayName: 'Release workspace',
        title: 'Release', status: 'active',
      }],
      nextCursor: null,
    });

    renderOperatorPanel(<MemoryRouter initialEntries={['/task/task-1/workspace']}><Routes><Route path="/task/:taskId/workspace" element={<TaskPage />} /></Routes></MemoryRouter>);

    expect(await screen.findByText('Terminal root: root-release')).toBeInTheDocument();
    expect(workspace.listProjects).toHaveBeenCalled();
  });

  it('treats an empty project root reference as no registered root', async () => {
    useProductShellStore.setState({
      projects: [{ projectId: 'project-1', rootRef: '', rootDisplayName: '' }],
      tasks: [{ id: 'task-1', projectId: 'project-1', title: 'Prepare release', createdAt: '2026-07-24T12:00:00Z', status: 'active' }],
    });

    renderOperatorPanel(<MemoryRouter initialEntries={['/task/task-1/workspace']}><Routes><Route path="/task/:taskId/workspace" element={<TaskPage />} /></Routes></MemoryRouter>);

    expect(await screen.findByText('Terminal root: runtime-root')).toBeInTheDocument();
  });

  it('starts with the workspace chooser when no tabs were saved', async () => {
    renderOperatorPanel(<MemoryRouter initialEntries={['/task/task-1/workspace']}><Routes><Route path="/task/:taskId/workspace" element={<TaskPage />} /></Routes></MemoryRouter>);

    expect(await screen.findByText('Workspace tabs: none')).toBeInTheDocument();
  });

  it('restores task-scoped workspace tabs and focus after the renderer remounts', async () => {
    sessionStorage.setItem('imperaos.workspace-tabs.task-1', JSON.stringify({
      tabs: [{ id: 'terminal-restored', kind: 'terminal', title: 'Terminal' }],
      activeTabId: 'terminal-restored',
    }));

    renderOperatorPanel(<MemoryRouter initialEntries={['/task/task-1/workspace']}><Routes><Route path="/task/:taskId/workspace" element={<TaskPage />} /></Routes></MemoryRouter>);

    expect(await screen.findByText('Workspace tabs: Terminal')).toBeInTheDocument();
    expect(screen.getByText('Active workspace tab: Terminal')).toBeInTheDocument();
  });

  it.each([
    ['terminal', 'Terminal'],
    ['browser', 'Browser'],
    ['preview', 'Preview'],
  ])('keeps an explicitly opened %s surface active after workspace navigation', async (buttonName, expectedTab) => {
    const { user } = renderOperatorPanel(
      <MemoryRouter initialEntries={['/task/task-1']}>
        <Routes>
          <Route path="/task/:taskId" element={<TaskPage />} />
          <Route path="/task/:taskId/workspace" element={<TaskPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await user.click(screen.getByRole('button', { name: `Open ${buttonName}` }));

    expect(await screen.findByText(`Workspace tabs: ${expectedTab}`)).toBeInTheDocument();
    expect(screen.getByText(`Active workspace tab: ${expectedTab}`)).toBeInTheDocument();
  });

  it('keeps separately opened artifacts in separate workspace tabs', async () => {
    const { user } = renderOperatorPanel(
      <MemoryRouter initialEntries={['/task/task-1/workspace']}>
        <Routes><Route path="/task/:taskId/workspace" element={<TaskPage />} /></Routes>
      </MemoryRouter>,
    );
    await screen.findByText('Workspace tabs: none');
    await user.click(screen.getByRole('button', { name: 'Open another artifact tab' }));

    await user.click(screen.getByRole('button', { name: 'Open another artifact tab' }));

    expect(await screen.findByText('Workspace tabs: Artifacts, Artifacts')).toBeInTheDocument();
  });

  it('persists completed assistant action references as durable task links', async () => {
    assistant.state.turns = [{
      id: 'turn-release', userMessage: { id: 'user-release', text: 'Prepare release', createdAtUtc: '2026-07-25T00:00:00Z' },
      assistantMessage: {
        id: 'assistant-release', text: 'Release prepared', findings: [], timeline: [], proposedAction: null,
        approval: { approvalId: 'approval-release', title: 'Release', status: 'pending', risk: 'medium', detailLoaded: false },
        referencedRuns: [{ id: 'run-release' }], referencedArtifacts: [{ name: 'Release plan', artifactId: 'artifact-release', openable: true }],
        parts: [], metrics: null, warning: null, error: null,
      },
      composerControls: null, startedAtUtc: '2026-07-25T00:00:00Z', completedAtUtc: '2026-07-25T00:00:01Z', status: 'completed', eventSequence: 1,
    }];
    workspace.addLink.mockResolvedValue({});

    renderOperatorPanel(<MemoryRouter initialEntries={['/task/task-1']}><Routes><Route path="/task/:taskId" element={<TaskPage />} /></Routes></MemoryRouter>);

    await waitFor(() => expect(workspace.addLink).toHaveBeenCalledWith('task-1', 'artifact', 'artifact-release'));
    expect(workspace.addLink).toHaveBeenCalledWith('task-1', 'run', 'run-release');
    expect(workspace.addLink).toHaveBeenCalledWith('task-1', 'approval', 'approval-release');
  });
});
