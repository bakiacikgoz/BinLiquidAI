import { screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
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
const workspace = vi.hoisted(() => ({ addLink: vi.fn(), addMessage: vi.fn(), getTask: vi.fn(), listLinks: vi.fn(), listMessages: vi.fn(), updateTask: vi.fn() }));

vi.mock('../adapters/useProductAssistant', () => ({ useProductAssistant: () => assistant }));
vi.mock('../adapters/productWorkspaceClient', () => ({ productWorkspaceClient: workspace }));
vi.mock('../workspace/WorkSurface', () => ({ WorkSurface: () => null }));
vi.mock('../workspace/ProductArtifactWorkspace', () => ({ ProductArtifactWorkspace: () => null }));
vi.mock('../workspace/WorkspaceTabs', () => ({ WorkspaceTabs: ({ tabs }: { tabs: Array<{ title: string }> }) => <p>Workspace tabs: {tabs.map((tab) => tab.title).join(', ') || 'none'}</p> }));

import { renderOperatorPanel } from '../../test/render';
import { useProductShellStore } from '../state/productShellStore';
import { TaskPage } from './TaskPage';

describe('TaskPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    workspace.addMessage.mockResolvedValue({});
    workspace.addLink.mockResolvedValue({});
    workspace.listMessages.mockResolvedValue({ messages: [] });
    workspace.listLinks.mockResolvedValue({ links: [] });
    workspace.updateTask.mockResolvedValue({
      taskId: 'task-1', title: 'Prepare release', status: 'active', assistantSessionId: 'session-task-1',
      reasoningEffort: 'high', speedProfile: 'standard', approvalProfile: 'risk_based',
      createdAtUtc: '2026-07-24T12:00:00Z', updatedAtUtc: '2026-07-24T12:00:00Z',
    });
    useProductShellStore.setState({
      tasks: [{ id: 'task-1', title: 'Prepare release', createdAt: '2026-07-24T12:00:00Z', status: 'active', assistantSessionId: 'session-task-1' }],
      selectedTaskId: null,
    });
  });

  it('sends the persisted first prompt exactly once after task navigation', async () => {
    const runtimeSettings = {
      assistantProvider: 'ollama', assistantFallbackProvider: '', assistantModel: 'qwen3.5:4b', assistantHfModelId: '',
    };
    const controls = { contextAttachmentKinds: ['artifact_summary'], toolIntents: ['inspect_run'] };
    renderOperatorPanel(<MemoryRouter initialEntries={[{ pathname: '/task/task-1', state: { initialMessage: 'Prepare a release', runtimeSettings, controls } }]}><Routes><Route path="/task/:taskId" element={<TaskPage />} /></Routes></MemoryRouter>);

    await waitFor(() => expect(assistant.actions.send).toHaveBeenCalledWith('Prepare a release', {
      ...runtimeSettings, reasoningEffort: 'medium', speedProfile: 'standard', approvalProfile: 'risk_based',
    }, controls));
    expect(workspace.addMessage).not.toHaveBeenCalledWith('task-1', 'user', 'Prepare a release');
  });

  it('persists a changed task reasoning profile before the next assistant turn', async () => {
    const { user } = renderOperatorPanel(<MemoryRouter initialEntries={['/task/task-1']}><Routes><Route path="/task/:taskId" element={<TaskPage />} /></Routes></MemoryRouter>);

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

    renderOperatorPanel(<MemoryRouter initialEntries={['/task/task-1']}><Routes><Route path="/task/:taskId" element={<TaskPage />} /><Route path="/" element={<p>Fallback route</p>} /></Routes></MemoryRouter>);

    expect(await screen.findByRole('heading', { name: 'Prepare release' })).toBeInTheDocument();
    expect(workspace.getTask).toHaveBeenCalledWith('task-1');
    expect(screen.queryByText('Fallback route')).not.toBeInTheDocument();
  });

  it('restores the workspace surface from the durable workspace route', async () => {
    renderOperatorPanel(<MemoryRouter initialEntries={['/task/task-1/workspace']}><Routes><Route path="/task/:taskId/workspace" element={<TaskPage />} /></Routes></MemoryRouter>);

    expect(await screen.findByText('Workspace tabs: Artifacts')).toBeInTheDocument();
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
