import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { DEFAULT_SETTINGS } from '../settings';
import { useAssistantSession, type AssistantContextSnapshot } from './useAssistantSession';

const bridgeMocks = vi.hoisted(() => ({
  startAssistantTurn: vi.fn(),
  listenAssistantEvents: vi.fn(),
}));

vi.mock('../bridge', () => ({
  startAssistantTurn: bridgeMocks.startAssistantTurn,
  listenAssistantEvents: bridgeMocks.listenAssistantEvents,
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
});
