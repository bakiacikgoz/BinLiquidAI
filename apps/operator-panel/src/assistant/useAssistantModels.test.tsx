import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { DEFAULT_SETTINGS } from '../settings';
import { useAssistantModels } from './useAssistantModels';

const bridgeMocks = vi.hoisted(() => ({
  listAssistantModels: vi.fn(),
}));

vi.mock('../bridge', () => ({
  listAssistantModels: bridgeMocks.listAssistantModels,
  BridgeError: class BridgeError extends Error {
    readonly payload: {
      code: string;
      message: string;
      stderrPreview: string;
      command: string;
      retryable: boolean;
    };

    constructor(payload: {
      code: string;
      message: string;
      stderrPreview: string;
      command: string;
      retryable: boolean;
    }) {
      super(payload.message);
      this.name = 'BridgeError';
      this.payload = payload;
    }
  },
}));

function providerModels(models: unknown[] = []) {
  return {
    contractVersion: 'operator-panel.assistant-provider-models/v1',
    profile: 'balanced',
    provider: 'ollama',
    generatedAtUtc: '2026-06-07T00:00:00.000Z',
    providers: [
      {
        provider: 'ollama',
        available: true,
        selectedByConfig: true,
        models,
      },
    ],
  };
}

describe('useAssistantModels', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads and flattens assistant model discovery candidates', async () => {
    bridgeMocks.listAssistantModels.mockResolvedValue(
      providerModels([
        {
          provider: 'ollama',
          id: 'qwen3.5:4b',
          displayName: 'qwen3.5:4b',
          installed: true,
          configured: true,
          source: 'ollama',
          warnings: [],
        },
      ]),
    );

    const { result } = renderHook(() =>
      useAssistantModels({ settings: { ...DEFAULT_SETTINGS }, profile: 'balanced', provider: 'ollama' }),
    );

    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(result.current.models).toHaveLength(1);
    expect(result.current.models[0]?.id).toBe('qwen3.5:4b');
    expect(bridgeMocks.listAssistantModels).toHaveBeenCalledWith(
      expect.objectContaining({ profile: 'balanced' }),
      expect.objectContaining({ profile: 'balanced', provider: 'ollama', refresh: false }),
    );
  });

  it('reports an empty discovery state when no candidates are returned', async () => {
    bridgeMocks.listAssistantModels.mockResolvedValue(providerModels([]));

    const { result } = renderHook(() =>
      useAssistantModels({ settings: { ...DEFAULT_SETTINGS }, profile: 'balanced', provider: 'ollama' }),
    );

    await waitFor(() => expect(result.current.status).toBe('empty'));
    expect(result.current.models).toEqual([]);
  });

  it('surfaces model discovery errors', async () => {
    bridgeMocks.listAssistantModels.mockRejectedValue(new Error('discovery failed'));

    const { result } = renderHook(() =>
      useAssistantModels({ settings: { ...DEFAULT_SETTINGS }, profile: 'balanced', provider: 'ollama' }),
    );

    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.error).toEqual({
      code: 'MODEL_DISCOVERY_FAILED',
      message: 'discovery failed',
    });
  });
});
