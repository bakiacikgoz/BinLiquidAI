import { waitFor } from '@testing-library/react';
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
const workspace = vi.hoisted(() => ({ addMessage: vi.fn(), listMessages: vi.fn() }));

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
    useProductShellStore.setState({
      tasks: [{ id: 'task-1', title: 'Prepare release', createdAt: '2026-07-24T12:00:00Z', status: 'active', assistantSessionId: 'session-task-1' }],
      selectedTaskId: null,
    });
  });

  it('sends the persisted first prompt exactly once after task navigation', async () => {
    renderOperatorPanel(<MemoryRouter initialEntries={[{ pathname: '/task/task-1', state: { initialMessage: 'Prepare a release' } }]}><Routes><Route path="/task/:taskId" element={<TaskPage />} /></Routes></MemoryRouter>);

    await waitFor(() => expect(assistant.actions.send).toHaveBeenCalledWith('Prepare a release'));
    expect(workspace.addMessage).not.toHaveBeenCalledWith('task-1', 'user', 'Prepare a release');
  });
});
