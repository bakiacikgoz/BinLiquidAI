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
    content: { kind: 'document', schemaVersion: 1, language: 'en', pageMode: 'document', blocks: [] },
  };
}

describe('assistant artifact workspace controller hook', () => {
  it('appends later history pages without duplicating revisions', async () => {
    const current = documentResult().revision;
    const older = { ...current, revisionId: 'revision-0', revisionNumber: 0 };
    const history = vi.fn()
      .mockResolvedValueOnce({ items: [current], nextCursor: 'cursor-2' })
      .mockResolvedValueOnce({ items: [current, older], nextCursor: null });
    const bridge = { get: vi.fn().mockResolvedValue(documentResult()), history } as unknown as ArtifactBridge;
    const { result } = renderHook(() => useAssistantArtifactWorkspaceController({
      assistantState: createAssistantSession('session-1'),
      legacyArtifacts: [],
      selectedLegacyArtifactName: '',
      onSelectLegacyArtifact: vi.fn(),
      bridge,
    }));

    await act(async () => result.current.actions.openArtifact('artifact-1'));
    await act(async () => result.current.actions.loadMoreHistory('artifact-1'));

    expect(history).toHaveBeenNthCalledWith(2, { artifactId: 'artifact-1', cursor: 'cursor-2', limit: 50 });
    expect(result.current.history.map((revision) => revision.revisionId)).toEqual(['revision-1', 'revision-0']);
  });

  it('compares an immutable historical revision without replacing the dirty draft', async () => {
    const current = documentResult();
    current.revision = { ...current.revision, revisionId: 'revision-2', revisionNumber: 2 };
    current.artifact = { ...current.artifact, currentRevisionId: 'revision-2', currentRevisionNumber: 2 };
    const historical = documentResult();
    historical.content = {
      kind: 'document', schemaVersion: 1, language: 'en', pageMode: 'document',
      blocks: [{ id: 'historical-block', type: 'paragraph', props: {}, content: [], children: [] }],
    };
    const get = vi.fn()
      .mockResolvedValueOnce(current)
      .mockResolvedValueOnce(historical);
    const bridge = {
      get,
      history: vi.fn().mockResolvedValue({ items: [], nextCursor: null }),
    } as unknown as ArtifactBridge;
    const { result } = renderHook(() => useAssistantArtifactWorkspaceController({
      assistantState: createAssistantSession('session-1'),
      legacyArtifacts: [],
      selectedLegacyArtifactName: '',
      onSelectLegacyArtifact: vi.fn(),
      bridge,
    }));
    const dirtyDraft = {
      kind: 'document' as const, schemaVersion: 1 as const, language: 'en', pageMode: 'document' as const,
      blocks: [{ id: 'local-block', type: 'paragraph', props: {}, content: [], children: [] }],
    };

    await act(async () => result.current.actions.openArtifact('artifact-1'));
    act(() => result.current.actions.edit('artifact-1', dirtyDraft));
    await act(async () => result.current.actions.compareRevision('artifact-1', 'revision-1'));

    expect(get).toHaveBeenNthCalledWith(2, { artifactId: 'artifact-1', revisionId: 'revision-1' });
    expect(result.current.activeTab).toMatchObject({ dirty: true, draftContent: dirtyDraft });
    expect(result.current.comparison).toMatchObject({
      status: 'ready', artifactId: 'artifact-1', selectedRevisionId: 'revision-1',
      beforeRevisionNumber: 1, afterRevisionNumber: 2, dirtyDraftExcluded: true,
    });
    expect(result.current.comparison?.result?.entries).toEqual([
      expect.objectContaining({ scope: 'block', key: 'historical-block', change: 'removed' }),
    ]);

    await act(async () => result.current.actions.openArtifact('artifact-1'));
    expect(result.current.comparison).toBeNull();
    expect(result.current.activeTab).toMatchObject({ dirty: true, draftContent: dirtyDraft });
  });

  it('owns shell state and opens a typed artifact tab outside App.tsx', async () => {
    const bridge = {
      get: vi.fn().mockResolvedValue(documentResult()),
      list: vi.fn().mockResolvedValue({ items: [], nextCursor: null }),
      history: vi.fn().mockResolvedValue({ items: [], nextCursor: null }),
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

  it('activates an already-open artifact without replacing its dirty draft', async () => {
    const bridge = {
      get: vi.fn().mockResolvedValue(documentResult()),
      history: vi.fn().mockResolvedValue({ items: [], nextCursor: null }),
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
    const edited = {
      kind: 'document' as const,
      schemaVersion: 1 as const,
      language: 'en',
      pageMode: 'document' as const,
      blocks: [],
    };
    act(() => result.current.actions.edit('artifact-1', edited));

    await act(async () => result.current.actions.openArtifact('artifact-1'));

    expect(bridge.get).toHaveBeenCalledTimes(1);
    expect(result.current.activeTab).toMatchObject({ dirty: true, draftContent: edited });
  });

  it('normalizes bridge failures and resets shell state for a new chat', async () => {
    const bridge = {
      get: vi.fn().mockRejectedValue(new Error('C:/secret/path must not leak')),
      history: vi.fn().mockResolvedValue({ items: [], nextCursor: null }),
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

  it('restores history and exports the active document through controller actions', async () => {
    const restore = vi.fn().mockResolvedValue({ artifact: documentResult().artifact, revision: documentResult().revision });
    const beginExport = vi.fn().mockResolvedValue({
      cancelled: false,
      ticket: 'ticket-1',
      expiresInMs: 60_000,
      maxBytes: 1024,
    });
    const commitExport = vi.fn().mockResolvedValue({
      basename: 'launch-plan.md',
      sha256: 'b'.repeat(64),
      sizeBytes: 1,
    });
    const history = vi.fn().mockResolvedValue({ items: [], nextCursor: null });
    const bridge = {
      get: vi.fn().mockResolvedValue(documentResult()),
      history,
      restore,
      beginExport,
      commitExport,
      cancelExport: vi.fn(),
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
    await act(async () => result.current.actions.restore('artifact-1', 'revision-0'));

    expect(restore).toHaveBeenCalledWith(expect.objectContaining({
      artifactId: 'artifact-1',
      sourceRevisionId: 'revision-0',
      idempotencyKey: expect.stringMatching(/^restore:artifact-1:revision-0:/),
    }));
    expect(history).toHaveBeenCalledTimes(2);

    await act(async () => result.current.actions.exportDocument('artifact-1', 'markdown'));
    expect(beginExport).toHaveBeenCalledWith(expect.objectContaining({
      artifactId: 'artifact-1',
      revisionId: 'revision-1',
      format: 'markdown',
    }));
    expect(commitExport).toHaveBeenCalledWith('ticket-1', expect.anything());
    expect(commitExport.mock.calls[0][1].constructor.name).toBe('Uint8Array');
  });

  it('rejects restore for archived artifacts before invoking the bridge', async () => {
    const archived = documentResult();
    archived.artifact = { ...archived.artifact, status: 'archived', archivedAtUtc: '2026-07-16T10:00:00Z' };
    const restore = vi.fn();
    const bridge = {
      get: vi.fn().mockResolvedValue(archived),
      history: vi.fn().mockResolvedValue({ items: [], nextCursor: null }),
      restore,
    } as unknown as ArtifactBridge;
    const { result } = renderHook(() => useAssistantArtifactWorkspaceController({
      assistantState: createAssistantSession('session-1'),
      legacyArtifacts: [],
      selectedLegacyArtifactName: '',
      onSelectLegacyArtifact: vi.fn(),
      bridge,
    }));

    await act(async () => result.current.actions.openArtifact('artifact-1'));
    await act(async () => result.current.actions.restore('artifact-1', 'revision-0'));

    expect(restore).not.toHaveBeenCalled();
    expect(result.current.error?.code).toBe('ARTIFACT_RESTORE_FAILED');
  });

  it('persists a 900ms autosave and reloads the saved revision in a fresh controller', async () => {
    vi.useFakeTimers();
    let stored = documentResult();
    const mutate = vi.fn().mockImplementation(async (request) => {
      const revisionNumber = stored.revision.revisionNumber + 1;
      stored = {
        artifact: {
          ...stored.artifact,
          currentRevisionId: `revision-${revisionNumber}`,
          currentRevisionNumber: revisionNumber,
          etag: `etag-${revisionNumber}`,
        },
        revision: {
          ...stored.revision,
          revisionId: `revision-${revisionNumber}`,
          parentRevisionId: stored.revision.revisionId,
          revisionNumber,
          mutationType: 'replace_content',
          idempotencyKey: request.idempotencyKey,
          changeSummary: request.changeSummary,
        },
        content: request.content,
      };
      return { artifact: stored.artifact, revision: stored.revision, created: false, disposition: 'updated' };
    });
    const bridge = {
      get: vi.fn().mockImplementation(async () => stored),
      history: vi.fn().mockResolvedValue({ items: [], nextCursor: null }),
      mutate,
    } as unknown as ArtifactBridge;
    const options = {
      assistantState: createAssistantSession('session-1'),
      legacyArtifacts: [],
      selectedLegacyArtifactName: '',
      onSelectLegacyArtifact: vi.fn(),
      bridge,
    };
    const first = renderHook(() => useAssistantArtifactWorkspaceController(options));
    await act(async () => first.result.current.actions.openArtifact('artifact-1'));
    const edited = {
      kind: 'document' as const,
      schemaVersion: 1 as const,
      language: 'en',
      pageMode: 'document' as const,
      blocks: [
        {
          id: 'block-1',
          type: 'paragraph',
          props: {},
          content: [{ type: 'text', text: 'Saved after debounce', styles: {} }],
          children: [],
        },
      ],
    };

    act(() => first.result.current.actions.edit('artifact-1', edited));
    await act(async () => vi.advanceTimersByTimeAsync(899));
    expect(mutate).not.toHaveBeenCalled();
    await act(async () => vi.advanceTimersByTimeAsync(1));
    expect(mutate).toHaveBeenCalledTimes(1);
    expect(first.result.current.activeTab).toMatchObject({
      dirty: false,
      saveState: 'saved',
      revision: { revisionNumber: 2 },
    });

    first.unmount();
    vi.useRealTimers();
    const second = renderHook(() => useAssistantArtifactWorkspaceController(options));
    await act(async () => second.result.current.actions.openArtifact('artifact-1'));

    expect(second.result.current.activeTab).toMatchObject({
      dirty: false,
      revision: { revisionNumber: 2 },
      draftContent: edited,
    });
    second.unmount();
  });
});
