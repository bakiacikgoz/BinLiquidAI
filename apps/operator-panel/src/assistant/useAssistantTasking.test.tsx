import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { DEFAULT_SETTINGS } from '../settings';
import { useAssistantTasking } from './useAssistantTasking';

const bridgeMocks = vi.hoisted(() => ({
  planAssistantTask: vi.fn(),
  submitAssistantTask: vi.fn(),
}));

vi.mock('../bridge', () => ({
  planAssistantTask: bridgeMocks.planAssistantTask,
  submitAssistantTask: bridgeMocks.submitAssistantTask,
  BridgeError: class BridgeError extends Error {
    readonly payload: { code: string; message: string };

    constructor(payload: { code: string; message: string }) {
      super(payload.message);
      this.name = 'BridgeError';
      this.payload = payload;
    }
  },
}));

function taskPlan() {
  return {
    schemaVersion: 'assistant-tasking.plan/v1',
    proposalId: 'astp-hook',
    planHash: 'sha256:99719f8157f65dbb65e653d28c371889ed9e81cbb843b6f24700d31e2b023944',
    status: 'planned',
    policyPreview: {
      decision: 'allow',
      riskClass: 'read_only',
      approvalRequired: false,
      safeToSubmit: true,
      reasonCode: 'ASSISTANT_TASK_READ_ONLY_ALLOWED',
      blockedReasons: [],
    },
    safeToSubmit: true,
    blockedReasons: [],
  };
}

describe('useAssistantTasking', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('plans and submits governed assistant tasks through the bridge', async () => {
    bridgeMocks.planAssistantTask.mockResolvedValue(taskPlan());
    bridgeMocks.submitAssistantTask.mockResolvedValue({
      schemaVersion: 'assistant-tasking.submission/v1',
      proposalId: 'astp-hook',
      planHash: taskPlan().planHash,
      status: 'accepted',
      policyDecision: 'allow',
      reasonCode: 'ASSISTANT_TASK_READ_ONLY_ALLOWED',
      runId: 'agt-hook',
      approvalId: null,
      evidenceRef: null,
      replayStatus: null,
      idempotencyStatus: 'created',
      blockedReasons: [],
      nextActions: ['run.status'],
      generatedAtUtc: '2026-03-08T09:00:00Z',
    });

    const { result } = renderHook(() => useAssistantTasking({ ...DEFAULT_SETTINGS }));

    await result.current.planTask('read queue', { operatorId: 'operator-1' });
    await waitFor(() => expect(result.current.status).toBe('planned'));
    await result.current.submitTask('astp-hook', taskPlan().planHash, 'operator-1');

    await waitFor(() => expect(result.current.status).toBe('submitted'));
    expect(bridgeMocks.planAssistantTask).toHaveBeenCalledWith(
      expect.objectContaining({ profile: DEFAULT_SETTINGS.profile }),
      expect.objectContaining({ message: 'read queue', operatorId: 'operator-1' }),
    );
    expect(bridgeMocks.submitAssistantTask).toHaveBeenCalledWith(
      expect.objectContaining({ profile: DEFAULT_SETTINGS.profile }),
      expect.objectContaining({ proposalId: 'astp-hook', operatorId: 'operator-1' }),
    );
  });
});
