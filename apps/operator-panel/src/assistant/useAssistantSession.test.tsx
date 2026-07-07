import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { DEFAULT_SETTINGS } from '../settings';
import { useAssistantSession, type AssistantContextSnapshot } from './useAssistantSession';

const bridgeMocks = vi.hoisted(() => ({
  startAssistantTurn: vi.fn(),
  cancelAssistantTurn: vi.fn(),
  listenAssistantEvents: vi.fn(),
  isBridgePreviewMode: vi.fn(),
  searchAssistantSystemKnowledge: vi.fn(),
  submitAssistantTask: vi.fn(),
}));

vi.mock('../bridge', () => ({
  startAssistantTurn: bridgeMocks.startAssistantTurn,
  cancelAssistantTurn: bridgeMocks.cancelAssistantTurn,
  listenAssistantEvents: bridgeMocks.listenAssistantEvents,
  isBridgePreviewMode: bridgeMocks.isBridgePreviewMode,
  searchAssistantSystemKnowledge: bridgeMocks.searchAssistantSystemKnowledge,
  submitAssistantTask: bridgeMocks.submitAssistantTask,
}));

const emptyContext: AssistantContextSnapshot = {
  selectedRunId: '',
  selectedRunStatus: null,
  selectedRunEvents: [],
  selectedArtifacts: {},
  pendingApproval: null,
  systemHealth: null,
};

describe('useAssistantSession runtime metadata', () => {
  beforeEach(() => {
    bridgeMocks.startAssistantTurn.mockResolvedValue({
      contractVersion: '2.0',
      assistantTurnId: 'turn-test',
      sessionId: 'session-test',
      processId: null,
      status: 'started',
    });
    bridgeMocks.listenAssistantEvents.mockResolvedValue(() => undefined);
    bridgeMocks.cancelAssistantTurn.mockResolvedValue({
      contractVersion: '2.0',
      assistantTurnId: 'turn-test',
      sessionId: 'session-test',
      processId: null,
      status: 'cancelled',
    });
    bridgeMocks.isBridgePreviewMode.mockReturnValue(false);
    bridgeMocks.searchAssistantSystemKnowledge.mockResolvedValue({
      status: 'ready',
      intent: 'agent_task',
      blockingReasons: [],
      context: {
        status: 'available',
        identityBrief: 'local knowledge',
        answerRules: [],
        sources: [],
        contextText: '',
        omittedSources: [],
        blockingReasons: [],
      },
    });
    bridgeMocks.submitAssistantTask.mockResolvedValue({
      schemaVersion: 'assistant-tasking.submission/v1',
      proposalId: 'astp-session',
      planHash: 'sha256:99719f8157f65dbb65e653d28c371889ed9e81cbb843b6f24700d31e2b023944',
      status: 'accepted',
      policyDecision: 'allow',
      reasonCode: 'ASSISTANT_TASK_READ_ONLY_ALLOWED',
      runId: 'agt-session',
      approvalId: null,
      evidenceRef: null,
      replayStatus: null,
      idempotencyStatus: 'created',
      blockedReasons: [],
      nextActions: ['run.status'],
      generatedAtUtc: '2026-03-08T09:00:00Z',
    });
    vi.clearAllMocks();
  });

  it('passes selected provider and model settings into startAssistantTurn', async () => {
    const settings = {
      ...DEFAULT_SETTINGS,
      assistantProvider: 'ollama',
      assistantFallbackProvider: 'transformers',
      assistantModel: 'qwen3.5:4b',
      assistantHfModelId: '',
    };
    const { result } = renderHook(() => useAssistantSession(settings, () => emptyContext));

    await act(async () => {
      await result.current.actions.send('Summarize the active run.');
    });

    await waitFor(() => expect(bridgeMocks.startAssistantTurn).toHaveBeenCalledTimes(1));
    expect(bridgeMocks.startAssistantTurn).toHaveBeenCalledWith(
      expect.objectContaining(settings),
      expect.objectContaining({
        profile: 'balanced',
        provider: 'ollama',
        fallbackProvider: 'transformers',
        model: 'qwen3.5:4b',
        hfModelId: undefined,
      }),
    );
  });

  it('passes undefined runtime overrides when profile defaults are selected', async () => {
    const { result } = renderHook(() => useAssistantSession({ ...DEFAULT_SETTINGS }, () => emptyContext));

    await act(async () => {
      await result.current.actions.send('Use profile defaults.');
    });

    await waitFor(() => expect(bridgeMocks.startAssistantTurn).toHaveBeenCalledTimes(1));
    expect(bridgeMocks.startAssistantTurn).toHaveBeenCalledWith(
      expect.any(Object),
      expect.objectContaining({
        profile: 'balanced',
        provider: undefined,
        fallbackProvider: undefined,
        model: undefined,
        hfModelId: undefined,
      }),
    );
  });

  it('applies preview assistant events through the reducer and reaches a final state', async () => {
    bridgeMocks.isBridgePreviewMode.mockReturnValue(true);
    const { result } = renderHook(() => useAssistantSession({ ...DEFAULT_SETTINGS }, () => emptyContext));

    await act(async () => {
      await result.current.actions.send('Preview assistant response.');
    });

    await waitFor(() => expect(result.current.state.status).toBe('completed'));
    expect(result.current.state.turns[0]?.assistantMessage.text).toContain('approval gate');
    expect(result.current.state.turns[0]?.completedAtUtc).toBeTruthy();
  });

  it('cancels the active assistant turn without surfacing an error', async () => {
    const { result } = renderHook(() => useAssistantSession({ ...DEFAULT_SETTINGS }, () => emptyContext));

    await act(async () => {
      await result.current.actions.send('Start a long response.');
    });

    await waitFor(() => expect(result.current.state.status).toBe('starting'));

    await act(async () => {
      await result.current.actions.cancel();
    });

    await waitFor(() => expect(result.current.state.status).toBe('cancelled'));
    expect(bridgeMocks.cancelAssistantTurn).toHaveBeenCalledWith(expect.any(Object), expect.stringMatching(/^assistant-turn-/));
    expect(result.current.state.error).toBeNull();
  });

  it('submits a task proposal with the confirmed plan hash', async () => {
    const planHash = 'sha256:99719f8157f65dbb65e653d28c371889ed9e81cbb843b6f24700d31e2b023944';
    const { result } = renderHook(() =>
      useAssistantSession({ ...DEFAULT_SETTINGS, operatorId: 'operator-1' }, () => emptyContext),
    );

    await act(async () => {
      await result.current.actions.send('Plan a governed task.');
    });
    await waitFor(() => expect(result.current.state.turns).toHaveLength(1));
    const turn = result.current.state.turns[0];

    act(() => {
      result.current.actions.applyEvent({
        contractVersion: '2.0',
        assistantTurnId: turn.id,
        sessionId: result.current.state.sessionId,
        event: 'task_plan',
        sequence: 2,
        timestampUtc: '2026-03-08T09:00:00Z',
        data: {
          proposalId: 'astp-session',
          planHash,
          status: 'planned',
          intentKind: 'plan_agent_task',
          taskSummary: 'Read queue',
          riskClass: 'read_only',
          policyPreview: {
            decision: 'allow',
            riskClass: 'read_only',
            approvalRequired: false,
            safeToSubmit: true,
            reasonCode: 'ASSISTANT_TASK_READ_ONLY_ALLOWED',
            blockedReasons: [],
          },
          approvalRequired: false,
          submitMode: 'proposal_first',
          evidenceExpectation: { mode: 'hash_only_redacted', expectedRefs: [], rawContentPersisted: false },
          safeToSubmit: true,
          blockedReasons: [],
          sourceRefs: [],
          createdAtUtc: '2026-03-08T09:00:00Z',
        },
      });
    });
    await waitFor(() => expect(result.current.state.turns[0]?.assistantMessage.taskPlan?.proposalId).toBe('astp-session'));

    await act(async () => {
      await result.current.actions.submitTaskProposal('astp-session', planHash);
    });

    expect(bridgeMocks.submitAssistantTask).toHaveBeenCalledWith(
      expect.objectContaining({ operatorId: 'operator-1' }),
      { proposalId: 'astp-session', confirmPlanHash: planHash, operatorId: 'operator-1' },
    );
    await waitFor(() => expect(result.current.state.turns[0]?.assistantMessage.taskSubmission?.runId).toBe('agt-session'));
  });
});
