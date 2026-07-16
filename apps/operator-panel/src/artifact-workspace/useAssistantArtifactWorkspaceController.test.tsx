import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { createAssistantSession } from '../assistant/assistantMappers';
import type { ArtifactBridge } from './artifactBridge';
import type { ArtifactReadResult } from './artifactContracts';
import { useAssistantArtifactWorkspaceController } from './useAssistantArtifactWorkspaceController';

function documentResult(): ArtifactReadResult {
  return {
    artifact: {
      artifactId: 'artifact-1',
      workspaceId: 'workspace-1',
      kind: 'document',
      title: 'Launch plan',
      status: 'active',
      schemaVersion: 1,
      dataClass: 'confidential',
      currentRevisionId: 'revision-1',
      currentRevisionNumber: 1,
      sourceSessionId: null,
      sourceTurnId: null,
      createdByType: 'assistant',
      createdById: 'assistant-1',
      updatedById: 'assistant-1',
      createdAtUtc: '2026-07-16T09:00:00Z',
      updatedAtUtc: '2026-07-16T09:00:00Z',
      archivedAtUtc: null,
      etag: 'etag-1',
      metadata: {},
    },
    revision: {
      revisionId: 'revision-1',
      artifactId: 'artifact-1',
      parentRevisionId: null,
      baseRevisionId: null,
      revisionNumber: 1,
      mutationType: 'create',
      contentRelpath: 'workspace-1/artifact-1/revision-1.json',
      contentSha256: 'a'.repeat(64),
      contentSizeBytes: 32,
      contentEncoding: 'json',
      changeSummary: 'Created',
      authorType: 'assistant',
      authorId: 'assistant-1',
      idempotencyKey: 'create-1',
      createdAtUtc: '2026-07-16T09:00:00Z',
    },
    content: { kind: 'document', schemaVersion: 1, blocks: [] },
  };
}

describe('assistant artifact workspace controller hook', () => {
  it('owns shell state and opens a typed artifact tab outside App.tsx', async () => {
    const bridge = {
      get: vi.fn().mockResolvedValue(documentResult()),
    } as unknown as ArtifactBridge;
    const onSelectLegacyArtifact = vi.fn();
    const { result } = renderHook(() =>
      useAssistantArtifactWorkspaceController({
        assistantState: createAssistantSession('session-1'),
        legacyArtifacts: [{ name: 'status.json', value: { status: 'ok' } }],
        selectedLegacyArtifactName: 'status.json',
        onSelectLegacyArtifact,
        bridge,
      }),
    );

    expect(result.current.open).toBe(false);
    expect(result.current.available).toBe(true);
    act(() => result.current.actions.toggle());
    expect(result.current.open).toBe(true);

    await act(async () => result.current.actions.openArtifact('artifact-1'));

    await waitFor(() => expect(result.current.activeTab?.artifact.artifactId).toBe('artifact-1'));
    expect(result.current.state.tabs).toHaveLength(1);
    expect(result.current.loadingArtifactId).toBeNull();
    expect(result.current.error).toBeNull();
    expect(bridge.get).toHaveBeenCalledWith({ artifactId: 'artifact-1' });

    act(() => result.current.actions.selectLegacyArtifact('status.json'));
    expect(onSelectLegacyArtifact).toHaveBeenCalledWith('status.json');
  });

  it('normalizes bridge failures and resets shell state for a new chat', async () => {
    const bridge = {
      get: vi.fn().mockRejectedValue(new Error('C:/secret/path must not leak')),
    } as unknown as ArtifactBridge;
    const { result } = renderHook(() =>
      useAssistantArtifactWorkspaceController({
        assistantState: createAssistantSession('session-1'),
        legacyArtifacts: [],
        selectedLegacyArtifactName: '',
        onSelectLegacyArtifact: vi.fn(),
        bridge,
      }),
    );

    await act(async () => result.current.actions.openArtifact('artifact-1'));
    expect(result.current.error).toEqual({
      code: 'ARTIFACT_WORKSPACE_OPEN_FAILED',
      message: 'The artifact could not be opened.',
      retryable: true,
    });

    act(() => result.current.actions.reset());
    expect(result.current.open).toBe(false);
    expect(result.current.error).toBeNull();
  });
});
