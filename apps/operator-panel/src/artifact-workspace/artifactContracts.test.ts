import { describe, expect, it } from 'vitest';

import { ArtifactReadResultSchema } from './artifactContracts';

const valid = {
  artifact: {
    artifactId: 'artifact-1', workspaceId: 'workspace-1', kind: 'document', title: 'Plan', status: 'active',
    schemaVersion: 1, dataClass: 'internal', currentRevisionId: 'revision-1', currentRevisionNumber: 1,
    sourceSessionId: null, sourceTurnId: null, createdByType: 'user', createdById: 'user-1', updatedById: 'user-1',
    createdAtUtc: '2026-07-16T08:00:00Z', updatedAtUtc: '2026-07-16T08:00:00Z', archivedAtUtc: null,
    etag: 'etag-1', metadata: {},
  },
  revision: {
    revisionId: 'revision-1', artifactId: 'artifact-1', parentRevisionId: null, baseRevisionId: null,
    revisionNumber: 1, mutationType: 'create', contentRelpath: 'workspace-1/artifact-1/revision-1.json',
    contentSha256: 'a'.repeat(64), contentSizeBytes: 32, contentEncoding: 'json', changeSummary: 'Created',
    authorType: 'user', authorId: 'user-1', idempotencyKey: 'create-1', createdAtUtc: '2026-07-16T08:00:00Z',
  },
  content: { kind: 'document', schemaVersion: 1, language: 'en', pageMode: 'document', blocks: [] },
};

describe('artifact read result contract', () => {
  it.each([
    ['revision identity', { ...valid, revision: { ...valid.revision, artifactId: 'artifact-2' } }],
    ['content kind', { ...valid, content: { kind: 'code', schemaVersion: 1 } }],
    ['content schema', { ...valid, content: { ...valid.content, schemaVersion: 2 } }],
  ])('rejects cross-boundary %s mismatches', (_label, payload) => {
    expect(ArtifactReadResultSchema.safeParse(payload).success).toBe(false);
  });
});
