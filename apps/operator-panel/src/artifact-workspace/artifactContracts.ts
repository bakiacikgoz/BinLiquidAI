import { z } from 'zod';


export const ARTIFACT_RPC_CONTRACT_VERSION = '1.0' as const;

const boundedId = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/);
const utcTimestamp = z.string().datetime({ offset: true });
const sha256 = z.string().regex(/^[0-9a-f]{64}$/);

export const ArtifactKindSchema = z.enum([
  'document',
  'form',
  'code',
  'flow',
  'spreadsheet',
  'canvas',
  'slides',
]);
export const ArtifactStatusSchema = z.enum(['draft', 'active', 'archived', 'blocked', 'corrupt']);
export const ArtifactDataClassSchema = z.enum([
  'public',
  'internal',
  'confidential',
  'regulated',
]);
export const PrincipalTypeSchema = z.enum(['user', 'assistant', 'system', 'import']);
export const ArtifactMutationTypeSchema = z.enum([
  'create',
  'replace_content',
  'json_patch',
  'text_edit',
  'cell_patch',
  'slide_patch',
  'restore',
  'duplicate',
  'import_evidence',
]);

export const ArtifactDescriptorSchema = z
  .object({
    artifactId: boundedId,
    workspaceId: boundedId,
    kind: ArtifactKindSchema,
    title: z.string().min(1).max(200),
    status: ArtifactStatusSchema,
    schemaVersion: z.number().int().min(1).max(1000),
    dataClass: ArtifactDataClassSchema,
    currentRevisionId: boundedId,
    currentRevisionNumber: z.number().int().min(1),
    sourceSessionId: boundedId.nullable(),
    sourceTurnId: boundedId.nullable(),
    createdByType: PrincipalTypeSchema,
    createdById: boundedId,
    updatedById: boundedId,
    createdAtUtc: utcTimestamp,
    updatedAtUtc: utcTimestamp,
    archivedAtUtc: utcTimestamp.nullable(),
    etag: z.string().min(1).max(256),
    metadata: z.record(z.string(), z.json()),
  })
  .strict();

export const ArtifactRevisionSchema = z
  .object({
    revisionId: boundedId,
    artifactId: boundedId,
    parentRevisionId: boundedId.nullable(),
    baseRevisionId: boundedId.nullable(),
    revisionNumber: z.number().int().min(1),
    mutationType: ArtifactMutationTypeSchema,
    contentRelpath: z.string().min(1).max(512),
    contentSha256: sha256,
    contentSizeBytes: z.number().int().min(0).max(100 * 1024 * 1024),
    contentEncoding: z.enum(['utf-8', 'json', 'binary']),
    changeSummary: z.string().max(500),
    authorType: PrincipalTypeSchema,
    authorId: boundedId,
    idempotencyKey: boundedId,
    createdAtUtc: utcTimestamp,
  })
  .strict();

export const ArtifactContentSchema = z
  .object({
    kind: ArtifactKindSchema,
    schemaVersion: z.number().int().min(1).max(1000),
  })
  .passthrough();

export const ArtifactReadResultSchema = z
  .object({
    artifact: ArtifactDescriptorSchema,
    revision: ArtifactRevisionSchema,
    content: ArtifactContentSchema,
  })
  .strict()
  .superRefine((value, context) => {
    if (value.revision.artifactId !== value.artifact.artifactId) {
      context.addIssue({ code: 'custom', path: ['revision', 'artifactId'], message: 'Revision artifact identity mismatch.' });
    }
    if (value.content.kind !== value.artifact.kind) {
      context.addIssue({ code: 'custom', path: ['content', 'kind'], message: 'Artifact content kind mismatch.' });
    }
    if (value.content.schemaVersion !== value.artifact.schemaVersion) {
      context.addIssue({ code: 'custom', path: ['content', 'schemaVersion'], message: 'Artifact content schema mismatch.' });
    }
  });

export const ArtifactOperationResultSchema = z
  .object({
    artifact: ArtifactDescriptorSchema,
    revision: ArtifactRevisionSchema,
    created: z.boolean(),
    disposition: z.enum(['created', 'no_op', 'idempotent_replay', 'updated']),
  })
  .strict();

export const ArtifactMutationProposalResultSchema = z
  .object({
    proposal_id: boundedId,
    artifact_id: boundedId,
    base_revision_number: z.number().int().min(1),
    status: z.enum(['pending', 'applied', 'rejected', 'stale']),
    content_sha256: sha256,
    summary: z.string().max(500),
  })
  .strict()
  .transform((value) => ({
    proposalId: value.proposal_id,
    artifactId: value.artifact_id,
    baseRevisionNumber: value.base_revision_number,
    status: value.status,
    contentSha256: value.content_sha256,
    summary: value.summary,
  }));

export const ArtifactListWireSchema = z
  .object({
    items: z.array(ArtifactDescriptorSchema),
    next_cursor: z.string().nullable(),
  })
  .strict()
  .transform(({ items, next_cursor }) => ({ items, nextCursor: next_cursor }));

export const ArtifactHistoryWireSchema = z
  .object({
    items: z.array(ArtifactRevisionSchema),
    next_cursor: z.string().nullable(),
  })
  .strict()
  .transform(({ items, next_cursor }) => ({ items, nextCursor: next_cursor }));

export const ArtifactExportBeginResultSchema = z
  .object({
    cancelled: z.boolean(),
    ticket: z.string().min(1).nullable(),
    expiresInMs: z.number().int().positive().nullable(),
    maxBytes: z.number().int().positive(),
  })
  .strict();

export const ArtifactExportResultSchema = z
  .object({
    basename: z.string().min(1).max(255),
    sha256,
    sizeBytes: z.number().int().min(0),
  })
  .strict();

export const ArtifactExportCancelResultSchema = z.object({ cancelled: z.literal(true) }).strict();

export type ArtifactKind = z.infer<typeof ArtifactKindSchema>;
export type ArtifactStatus = z.infer<typeof ArtifactStatusSchema>;
export type ArtifactDataClass = z.infer<typeof ArtifactDataClassSchema>;
export type ArtifactMutationType = z.infer<typeof ArtifactMutationTypeSchema>;
export type ArtifactDescriptor = z.infer<typeof ArtifactDescriptorSchema>;
export type ArtifactRevision = z.infer<typeof ArtifactRevisionSchema>;
export type ArtifactContent = z.infer<typeof ArtifactContentSchema>;
export type ArtifactReadResult = z.infer<typeof ArtifactReadResultSchema>;
export type ArtifactOperationResult = z.infer<typeof ArtifactOperationResultSchema>;
export type ArtifactMutationProposalResult = z.output<typeof ArtifactMutationProposalResultSchema>;
export type ArtifactListResult = z.output<typeof ArtifactListWireSchema>;
export type ArtifactHistoryResult = z.output<typeof ArtifactHistoryWireSchema>;
export type ArtifactExportBeginResult = z.infer<typeof ArtifactExportBeginResultSchema>;
export type ArtifactExportResult = z.infer<typeof ArtifactExportResultSchema>;

export interface ArtifactListRequest {
  kind?: ArtifactKind;
  status?: ArtifactStatus;
  cursor?: string;
  limit?: number;
}

export interface ArtifactGetRequest {
  artifactId: string;
  revisionId?: string;
}

export interface ArtifactCreateRequest {
  artifactId?: string;
  kind: ArtifactKind;
  title: string;
  dataClass: ArtifactDataClass;
  content: ArtifactContent;
  idempotencyKey: string;
  sourceSessionId?: string;
  sourceTurnId?: string;
  metadata?: Record<string, unknown>;
}

export interface ArtifactMutationRequest {
  artifactId: string;
  expectedRevisionNumber: number;
  mutationType: ArtifactMutationType;
  content: ArtifactContent;
  idempotencyKey: string;
  changeSummary?: string;
  approvalGranted?: boolean;
  proposalId?: string;
}

export interface ArtifactMutationProposalRequest {
  proposalId?: string;
  artifactId: string;
  baseRevisionNumber: number;
  mutationType: ArtifactMutationType;
  content: ArtifactContent;
  idempotencyKey: string;
  summary?: string;
}

export interface ArtifactHistoryRequest {
  artifactId: string;
  cursor?: string;
  limit?: number;
}

export interface ArtifactRestoreRequest {
  artifactId: string;
  sourceRevisionId: string;
  expectedRevisionNumber: number;
  idempotencyKey: string;
  changeSummary?: string;
}

export interface ArtifactArchiveRequest {
  artifactId: string;
  expectedRevisionNumber: number;
}

export interface ArtifactDuplicateRequest {
  sourceArtifactId: string;
  artifactId?: string;
  title: string;
  idempotencyKey: string;
}

export interface ArtifactExportBeginRequest {
  artifactId: string;
  revisionId: string;
  format: string;
  suggestedName: string;
}
