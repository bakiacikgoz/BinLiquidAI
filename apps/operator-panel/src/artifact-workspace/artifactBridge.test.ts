import { afterEach, describe, expect, it, vi } from 'vitest';

import type { ArtifactDescriptor } from './artifactContracts';


const descriptor: ArtifactDescriptor = {
  artifactId: 'artifact-1',
  workspaceId: 'workspace-1',
  kind: 'document',
  title: 'Plan',
  status: 'draft',
  schemaVersion: 1,
  dataClass: 'internal',
  currentRevisionId: 'revision-1',
  currentRevisionNumber: 1,
  sourceSessionId: null,
  sourceTurnId: null,
  createdByType: 'user',
  createdById: 'user-1',
  updatedById: 'user-1',
  createdAtUtc: '2026-07-16T08:00:00Z',
  updatedAtUtc: '2026-07-16T08:00:00Z',
  archivedAtUtc: null,
  etag: 'etag-1',
  metadata: {},
};

function mockInvoke(data: unknown) {
  const invoke = vi.fn().mockResolvedValue({ ok: true, data, error: null });
  vi.doMock('@tauri-apps/api/core', () => ({ invoke }));
  return invoke;
}

describe('artifact bridge', () => {
  afterEach(() => {
    vi.doUnmock('@tauri-apps/api/core');
    vi.resetModules();
  });

  it('sends only versioned params through the governed Tauri command', async () => {
    const invoke = mockInvoke({ items: [descriptor], next_cursor: null });
    const { artifactBridge } = await import('./artifactBridge');

    const result = await artifactBridge.list({ kind: 'document', limit: 25 });

    expect(result).toEqual({ items: [descriptor], nextCursor: null });
    expect(invoke).toHaveBeenCalledWith('bridge_artifact_list', {
      payload: {
        params: { kind: 'document', limit: 25 },
        idempotencyKey: null,
        timeoutMs: 15_000,
      },
    });
  });

  it('binds mutation idempotency and validates successful response data', async () => {
    const invoke = mockInvoke({
      artifact: descriptor,
      revision: {
        revisionId: 'revision-2',
        artifactId: 'artifact-1',
        parentRevisionId: 'revision-1',
        baseRevisionId: null,
        revisionNumber: 2,
        mutationType: 'replace_content',
        contentRelpath: 'workspace-1/artifact-1/2/revision-2.json',
        contentSha256: 'a'.repeat(64),
        contentSizeBytes: 10,
        contentEncoding: 'json',
        changeSummary: 'Autosave',
        authorType: 'user',
        authorId: 'user-1',
        idempotencyKey: 'save-2',
        createdAtUtc: '2026-07-16T08:01:00Z',
      },
      created: false,
      disposition: 'updated',
    });
    const { artifactBridge } = await import('./artifactBridge');

    await artifactBridge.mutate({
      artifactId: 'artifact-1',
      expectedRevisionNumber: 1,
      mutationType: 'replace_content',
      content: { kind: 'document', schemaVersion: 1, language: 'tr', blocks: [] },
      idempotencyKey: 'save-2',
      changeSummary: 'Autosave',
    });

    expect(invoke).toHaveBeenCalledWith('bridge_artifact_mutate', {
      payload: expect.objectContaining({ idempotencyKey: 'save-2' }),
    });
  });

  it('fails closed when a successful native response violates the runtime contract', async () => {
    mockInvoke({ items: [{ ...descriptor, kind: 'unknown' }], next_cursor: null });
    const { ArtifactContractError, artifactBridge } = await import('./artifactBridge');

    await expect(artifactBridge.list({ limit: 25 })).rejects.toBeInstanceOf(ArtifactContractError);
  });

  it('preserves typed governed errors without exposing raw payloads', async () => {
    const invoke = vi.fn().mockResolvedValue({
      ok: false,
      data: null,
      error: {
        code: 'ARTIFACT_REVISION_CONFLICT',
        message: 'artifact revision is stale',
        stderrPreview: '',
        command: 'artifact.mutate',
        retryable: false,
      },
    });
    vi.doMock('@tauri-apps/api/core', () => ({ invoke }));
    const { ArtifactBridgeError, artifactBridge } = await import('./artifactBridge');

    const error = await artifactBridge.get({ artifactId: 'artifact-1' }).catch((caught) => caught);

    expect(error).toBeInstanceOf(ArtifactBridgeError);
    expect(error.code).toBe('ARTIFACT_REVISION_CONFLICT');
    expect(Object.keys(error)).not.toContain('stderrPreview');
  });
});
