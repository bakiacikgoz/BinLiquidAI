import { describe, expect, it, vi } from 'vitest';

import type { ArtifactBridge } from './artifactBridge';
import type { ArtifactContent, ArtifactReadResult } from './artifactContracts';
import {
  ArtifactWorkspaceController,
  artifactWorkspaceReducer,
  createArtifactWorkspaceState,
} from './workspaceController';


function loaded(text = 'v1'): ArtifactReadResult {
  return {
    artifact: {
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
    },
    revision: {
      revisionId: 'revision-1',
      artifactId: 'artifact-1',
      parentRevisionId: null,
      baseRevisionId: null,
      revisionNumber: 1,
      mutationType: 'create',
      contentRelpath: 'workspace-1/artifact-1/1/revision-1.json',
      contentSha256: 'a'.repeat(64),
      contentSizeBytes: 10,
      contentEncoding: 'json',
      changeSummary: 'Created',
      authorType: 'user',
      authorId: 'user-1',
      idempotencyKey: 'create-1',
      createdAtUtc: '2026-07-16T08:00:00Z',
    },
    content: { kind: 'document', schemaVersion: 1, text },
  };
}

describe('artifact workspace controller', () => {
  it('opens tabs once, tracks active tab, and marks edited content dirty', () => {
    let state = createArtifactWorkspaceState();
    state = artifactWorkspaceReducer(state, { type: 'opened', result: loaded() });
    state = artifactWorkspaceReducer(state, { type: 'opened', result: loaded() });
    const draft: ArtifactContent = { kind: 'document', schemaVersion: 1, text: 'v2' };
    state = artifactWorkspaceReducer(state, {
      type: 'edited',
      artifactId: 'artifact-1',
      content: draft,
    });

    expect(state.tabs).toHaveLength(1);
    expect(state.activeArtifactId).toBe('artifact-1');
    expect(state.tabs[0]).toMatchObject({ dirty: true, saveState: 'dirty', draftContent: draft });
  });

  it('guards dirty close and supports cancel or explicit discard', () => {
    let state = artifactWorkspaceReducer(createArtifactWorkspaceState(), {
      type: 'opened',
      result: loaded(),
    });
    state = artifactWorkspaceReducer(state, {
      type: 'edited',
      artifactId: 'artifact-1',
      content: { kind: 'document', schemaVersion: 1, text: 'v2' },
    });
    state = artifactWorkspaceReducer(state, { type: 'closeRequested', artifactId: 'artifact-1' });

    expect(state.closeGuard).toEqual({ artifactId: 'artifact-1', reason: 'dirty' });
    expect(state.tabs).toHaveLength(1);

    state = artifactWorkspaceReducer(state, { type: 'closeCancelled' });
    expect(state.closeGuard).toBeNull();
    state = artifactWorkspaceReducer(state, { type: 'closeRequested', artifactId: 'artifact-1' });
    state = artifactWorkspaceReducer(state, { type: 'closeDiscarded', artifactId: 'artifact-1' });
    expect(state.tabs).toHaveLength(0);
    expect(state.activeArtifactId).toBeNull();
  });

  it('records conflicts without replacing the local draft', () => {
    let state = artifactWorkspaceReducer(createArtifactWorkspaceState(), {
      type: 'opened',
      result: loaded(),
    });
    const draft: ArtifactContent = { kind: 'document', schemaVersion: 1, text: 'local' };
    state = artifactWorkspaceReducer(state, {
      type: 'edited',
      artifactId: 'artifact-1',
      content: draft,
    });
    state = artifactWorkspaceReducer(state, {
      type: 'saveConflicted',
      artifactId: 'artifact-1',
      remote: loaded('remote'),
    });

    expect(state.tabs[0]).toMatchObject({
      dirty: true,
      saveState: 'conflict',
      draftContent: draft,
      conflict: { remoteRevisionNumber: 1 },
    });
  });

  it('orchestrates open, restore, and archive through the typed bridge', async () => {
    const first = loaded();
    const restored = loaded('restored');
    restored.artifact.currentRevisionNumber = 2;
    restored.revision.revisionNumber = 2;
    const bridge = {
      get: vi.fn().mockResolvedValueOnce(first).mockResolvedValueOnce(restored),
      restore: vi.fn().mockResolvedValue({
        artifact: restored.artifact,
        revision: restored.revision,
        created: false,
        disposition: 'updated',
      }),
      archive: vi.fn().mockResolvedValue({
        artifact: { ...restored.artifact, status: 'archived' },
        revision: restored.revision,
        created: false,
        disposition: 'updated',
      }),
    } as unknown as ArtifactBridge;
    const controller = new ArtifactWorkspaceController(bridge);

    await controller.open('artifact-1');
    await controller.restore('artifact-1', 'revision-1', 'restore-1');
    await controller.archive('artifact-1');

    expect(bridge.restore).toHaveBeenCalledWith({
      artifactId: 'artifact-1',
      sourceRevisionId: 'revision-1',
      expectedRevisionNumber: 1,
      idempotencyKey: 'restore-1',
      changeSummary: 'Revision restored',
    });
    expect(controller.getState().tabs[0]).toMatchObject({
      dirty: false,
      saveState: 'idle',
      artifact: { status: 'archived', currentRevisionNumber: 2 },
    });
  });
});
