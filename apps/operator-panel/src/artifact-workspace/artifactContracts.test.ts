import { describe, expect, it } from 'vitest';

import codeParityFixture from '../../../../contracts/artifacts/fixtures/code-content-parity.v1.json';

import {
  ArtifactContentSchema,
  ArtifactFormSubmissionResultSchema,
  ArtifactReadResultSchema,
} from './artifactContracts';

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

describe('artifact form submission contract', () => {
  const result = {
    submissionId: 'submission-1',
    artifactId: 'artifact-1',
    schemaRevisionId: 'revision-1',
    status: 'accepted',
    responseSha256: 'b'.repeat(64),
    continuationAction: 'none',
    approvalId: null,
    reasonCode: 'FORM_CONTINUATION_NOT_REQUIRED',
    actionHash: null,
    disposition: 'created',
  };

  it('accepts the bounded result and rejects unknown or unsafe fields', () => {
    expect(ArtifactFormSubmissionResultSchema.safeParse(result).success).toBe(true);
    expect(ArtifactFormSubmissionResultSchema.safeParse({ ...result, rawResponse: { secret: true } }).success).toBe(false);
    expect(ArtifactFormSubmissionResultSchema.safeParse({ ...result, status: 'executed' }).success).toBe(false);
  });
});

describe('code artifact content contract', () => {
  it.each(codeParityFixture.cases)('$id', ({ content, expectedValid }) => {
    expect(ArtifactContentSchema.safeParse(content).success).toBe(expectedValid);
  });
});
