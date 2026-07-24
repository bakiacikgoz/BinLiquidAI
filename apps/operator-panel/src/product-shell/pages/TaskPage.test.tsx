import { screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const assistant = vi.hoisted(() => ({
  state: {
    sessionId: 'session-task-1', turns: [], activeTurnId: null, status: 'idle', selectedRunIds: [],
    referencedArtifacts: [], pendingApprovalId: null, error: null,
  },
  actions: {
    send: vi.fn(), newChat: vi.fn(), regenerate: vi.fn(), cancel: vi.fn(), applyEvent: vi.fn(),
    markApprovalDetailLoaded: vi.fn(), updateApprovalStatus: vi.fn(), appendSystemMessage: vi.fn(),
  },
}));
const workspace = vi.hoisted(() => ({ addMessage: vi.fn(), listMessages: vi.fn(), updateTask: vi.fn() }));

vi.mock('../adapters/useProductAssistant', () => ({ useProductAssistant: () => assistant }));
vi.mock('../adapters/productWorkspaceClient', () => ({ productWorkspaceClient: workspace }));
vi.mock('../workspace/WorkSurface', () => ({ WorkSurface: () => null }));
vi.mock('../workspace/ProductArtifactWorkspace', () => ({ ProductArtifactWorkspace: () => null }));

import { renderOperatorPanel } from '../../test/render';
import { useProductShellStore } from '../state/productShellStore';
import { TaskPage } from './TaskPage';

describe('TaskPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    workspace.listMessages.mockResolvedValue({ messages: [] });
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
});
