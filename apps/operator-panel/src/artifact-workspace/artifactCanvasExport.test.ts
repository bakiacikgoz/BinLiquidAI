import { describe, expect, it, vi } from 'vitest';

import type { ArtifactBridge } from './artifactBridge';
import { exportCanvasArtifact, serializeCanvasJson } from './artifactCanvasExport';
import type { ArtifactDescriptor, ArtifactRevision, CanvasArtifactContent } from './artifactContracts';

const content = {
  kind: 'canvas', schemaVersion: 2,
  snapshot: { objects: [{
    id: 'note-1', type: 'note', x: 1, y: 2, width: 200, height: 100,
    text: '<script>local text only</script>',
  }] },
  assetIds: [], embeds: 'deny', remoteAssets: 'deny',
} satisfies CanvasArtifactContent;
const artifact = {
  artifactId: 'canvas-1', workspaceId: 'workspace-1', kind: 'canvas', title: 'Board',
  status: 'active', schemaVersion: 2, dataClass: 'internal', currentRevisionId: 'revision-2',
  currentRevisionNumber: 2, sourceSessionId: null, sourceTurnId: null, createdByType: 'user',
  createdById: 'user-1', updatedById: 'user-1', createdAtUtc: '2026-07-16T08:00:00Z',
  updatedAtUtc: '2026-07-16T08:01:00Z', archivedAtUtc: null, etag: 'etag', metadata: {},
} satisfies ArtifactDescriptor;
const revision = {
  revisionId: 'revision-2', artifactId: artifact.artifactId, parentRevisionId: 'revision-1',
  baseRevisionId: null, revisionNumber: 2, schemaVersion: 2, mutationType: 'replace_content',
  contentRelpath: 'content/canvas.json', contentSha256: 'a'.repeat(64), contentSizeBytes: 100,
  contentEncoding: 'json', changeSummary: 'Board', authorType: 'user', authorId: 'user-1',
  idempotencyKey: 'save-1', createdAtUtc: '2026-07-16T08:01:00Z',
} satisfies ArtifactRevision;

describe('canvas fallback export', () => {
  it('serializes only the strict local canvas.v2 contract', () => {
    expect(new TextDecoder().decode(serializeCanvasJson(content))).toBe(`${JSON.stringify(content, null, 2)}\n`);
    expect(() => serializeCanvasJson({ ...content, remoteAssets: 'allow' })).toThrow();
    expect(() => serializeCanvasJson({ ...content, snapshot: { objects: [{ ...content.snapshot.objects[0], src: 'https://example.com' }] } })).toThrow();
    expect(() => serializeCanvasJson({
      kind: 'canvas', schemaVersion: 1, snapshot: { store: {} }, assetIds: [],
      embeds: 'deny', remoteAssets: 'deny', unexpected: true,
    })).toThrow();
  });

  it('keeps the legacy read-only JSON fallback exportable', async () => {
    const bridge = {
      beginExport: vi.fn().mockResolvedValue({ cancelled: true }),
    } as unknown as ArtifactBridge;
    await expect(exportCanvasArtifact({
      artifact: { ...artifact, schemaVersion: 1 },
      revision: { ...revision, schemaVersion: 1 },
      content: {
        kind: 'canvas', schemaVersion: 1, snapshot: { store: {} }, assetIds: [],
        embeds: 'deny', remoteAssets: 'deny',
      },
      bridge,
    })).resolves.toEqual({ status: 'cancelled' });
  });

  it('uses the canvas revision ticket and cancels oversized output', async () => {
    const bridge = {
      beginExport: vi.fn().mockResolvedValue({ cancelled: false, ticket: 'ticket-1', maxBytes: 2 }),
      commitExport: vi.fn(),
      cancelExport: vi.fn().mockResolvedValue(undefined),
    } as unknown as ArtifactBridge;
    await expect(exportCanvasArtifact({ artifact, revision, content, bridge })).rejects.toThrow(/size limit/i);
    expect(bridge.beginExport).toHaveBeenCalledWith(expect.objectContaining({
      artifactId: artifact.artifactId, revisionId: revision.revisionId, format: 'json',
    }));
    expect(bridge.cancelExport).toHaveBeenCalledWith('ticket-1');
  });
});
