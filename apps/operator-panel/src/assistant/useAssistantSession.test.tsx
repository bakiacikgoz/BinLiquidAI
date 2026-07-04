import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { DEFAULT_SETTINGS } from '../settings';
import { useAssistantSession, type AssistantContextSnapshot } from './useAssistantSession';

const bridgeMocks = vi.hoisted(() => ({
  startAssistantTurn: vi.fn(),
  cancelAssistantTurn: vi.fn(),
  listenAssistantEvents: vi.fn(),
  isBridgePreviewMode: vi.fn(),
}));

vi.mock('../bridge', () => ({
  startAssistantTurn: bridgeMocks.startAssistantTurn,
  cancelAssistantTurn: bridgeMocks.cancelAssistantTurn,
  listenAssistantEvents: bridgeMocks.listenAssistantEvents,
  isBridgePreviewMode: bridgeMocks.isBridgePreviewMode,
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
});
