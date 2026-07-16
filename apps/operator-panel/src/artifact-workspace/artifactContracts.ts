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

export const ArtifactLicenseCapabilitySchema = z.object({
  contractVersion: z.literal('artifact-license-capability/v1'),
  kind: z.enum(['spreadsheet', 'canvas']),
  enabled: z.boolean(),
  reasonCode: z.string().min(1).max(128).regex(/^ARTIFACT_LICENSE_[A-Z_]+$/),
}).strict().superRefine((capability, context) => {
  if (capability.enabled !== (capability.reasonCode === 'ARTIFACT_LICENSE_ENABLED')) {
    context.addIssue({ code: 'custom', path: ['reasonCode'], message: 'License capability reason does not match enabled state.' });
  }
});
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
    schemaVersion: z.number().int().min(1).max(1000),
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

export const CodeArtifactLanguageSchema = z.enum([
  'plaintext', 'bat', 'c', 'cpp', 'csharp', 'css', 'go', 'html', 'java', 'javascript',
  'json', 'markdown', 'powershell', 'python', 'rust', 'shell', 'sql', 'typescript', 'xml', 'yaml',
]);

const WINDOWS_DEVICE_NAME = /^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)/i;
const FORBIDDEN_FILENAME_CHARACTER = /[<>:"/\\|?*]/;
const CONTROL_OR_FORMAT_CHARACTER = /[\p{Cc}\p{Cf}]/u;

export const CodeArtifactContentSchema = z
  .object({
    kind: z.literal('code'),
    schemaVersion: z.literal(2),
    filename: z.string().min(1).max(255),
    language: CodeArtifactLanguageSchema,
    text: z.string().max(5 * 1024 * 1024),
    lineEnding: z.enum(['lf', 'crlf']).default('lf'),
    executionPolicy: z.literal('deny').default('deny'),
  })
  .strict()
  .superRefine((value, context) => {
    const invalidFilename = value.filename !== value.filename.normalize('NFC')
      || value.filename !== value.filename.trim()
      || value.filename === '.'
      || value.filename === '..'
      || value.filename.endsWith('.')
      || WINDOWS_DEVICE_NAME.test(value.filename)
      || FORBIDDEN_FILENAME_CHARACTER.test(value.filename)
      || CONTROL_OR_FORMAT_CHARACTER.test(value.filename);
    if (invalidFilename) {
      context.addIssue({ code: 'custom', path: ['filename'], message: 'Code filename is not portable.' });
    }
    const invalidLineEnding = value.lineEnding === 'lf'
      ? value.text.includes('\r')
      : /(^|[^\r])\n|\r(?!\n)/.test(value.text);
    if (invalidLineEnding) {
      context.addIssue({ code: 'custom', path: ['text'], message: 'Code text does not match lineEnding.' });
    }
  });

export const LegacyCodeArtifactContentSchema = z.object({
  kind: z.literal('code'),
  schemaVersion: z.literal(1),
  // Legacy v1 intentionally rejects NUL explicitly; strict v2 has the complete filename policy.
  // eslint-disable-next-line no-control-regex
  filename: z.string().min(1).max(255).regex(/^[^/\\:\u0000]+$/),
  language: z.string().min(1).max(64).regex(/^[a-z0-9_+-]+$/),
  text: z.string().max(5 * 1024 * 1024),
  lineEnding: z.enum(['lf', 'crlf']).default('lf'),
  executionPolicy: z.literal('deny').default('deny'),
}).strict();

const FlowPositionSchema = z.object({
  x: z.number().finite().min(-1_000_000).max(1_000_000),
  y: z.number().finite().min(-1_000_000).max(1_000_000),
}).strict();

const FlowNodeDataSchema = z.object({
  label: z.string().min(1).max(200).refine((value) => !CONTROL_OR_FORMAT_CHARACTER.test(value)),
  description: z.string().max(1_000).refine((value) => !CONTROL_OR_FORMAT_CHARACTER.test(value)).optional(),
  artifactId: boundedId.optional(),
}).strict();

const FlowNodeSchema = z.object({
  id: boundedId,
  type: z.enum(['input', 'output', 'process', 'decision', 'note', 'group', 'artifact']),
  position: FlowPositionSchema,
  data: FlowNodeDataSchema,
}).strict().superRefine((node, context) => {
  if (node.type === 'artifact' && node.data.artifactId === undefined) {
    context.addIssue({ code: 'custom', path: ['data', 'artifactId'], message: 'Artifact node requires artifactId.' });
  }
  if (node.type !== 'artifact' && node.data.artifactId !== undefined) {
    context.addIssue({ code: 'custom', path: ['data', 'artifactId'], message: 'artifactId is only valid for artifact nodes.' });
  }
});

const FlowEdgeSchema = z.object({
  id: boundedId,
  source: boundedId,
  target: boundedId,
  label: z.string().max(200).refine((value) => !CONTROL_OR_FORMAT_CHARACTER.test(value)).nullable().optional(),
}).strict();

export const FlowArtifactContentSchema = z.object({
  kind: z.literal('flow'),
  schemaVersion: z.literal(2),
  nodes: z.array(FlowNodeSchema).max(5_000),
  edges: z.array(FlowEdgeSchema).max(10_000),
  viewport: z.object({
    x: z.number().finite().min(-1_000_000).max(1_000_000),
    y: z.number().finite().min(-1_000_000).max(1_000_000),
    zoom: z.number().finite().min(0.05).max(8),
  }).strict(),
}).strict().superRefine((flow, context) => {
  const nodeIds = new Set<string>();
  flow.nodes.forEach((node, index) => {
    if (nodeIds.has(node.id)) context.addIssue({ code: 'custom', path: ['nodes', index, 'id'], message: 'Duplicate node ID.' });
    nodeIds.add(node.id);
  });
  const edgeIds = new Set<string>();
  const incoming = new Map(flow.nodes.map((node) => [node.id, 0]));
  const adjacency = new Map(flow.nodes.map((node) => [node.id, [] as string[]]));
  flow.edges.forEach((edge, index) => {
    if (edgeIds.has(edge.id)) context.addIssue({ code: 'custom', path: ['edges', index, 'id'], message: 'Duplicate edge ID.' });
    edgeIds.add(edge.id);
    if (!nodeIds.has(edge.source)) context.addIssue({ code: 'custom', path: ['edges', index, 'source'], message: 'Unknown source node.' });
    if (!nodeIds.has(edge.target)) context.addIssue({ code: 'custom', path: ['edges', index, 'target'], message: 'Unknown target node.' });
    if (edge.source === edge.target) context.addIssue({ code: 'custom', path: ['edges', index], message: 'Self-loops are forbidden.' });
    if (nodeIds.has(edge.source) && nodeIds.has(edge.target) && edge.source !== edge.target) {
      adjacency.get(edge.source)?.push(edge.target);
      incoming.set(edge.target, (incoming.get(edge.target) ?? 0) + 1);
    }
  });
  const pending = [...incoming].filter(([, count]) => count === 0).map(([id]) => id);
  let visited = 0;
  while (pending.length > 0) {
    const id = pending.pop() as string;
    visited += 1;
    adjacency.get(id)?.forEach((target) => {
      const next = (incoming.get(target) ?? 0) - 1;
      incoming.set(target, next);
      if (next === 0) pending.push(target);
    });
  }
  if (visited !== flow.nodes.length) context.addIssue({ code: 'custom', path: ['edges'], message: 'Flow must be acyclic.' });
});

const LegacyFlowArtifactContentSchema = z.object({
  kind: z.literal('flow'),
  schemaVersion: z.literal(1),
}).passthrough();

function validXlsxAddress(address: string): boolean {
  const match = /^([A-Z]{1,3})([1-9][0-9]{0,6})$/.exec(address);
  if (!match) return false;
  const column = [...match[1]].reduce(
    (value, character) => value * 26 + character.charCodeAt(0) - 64,
    0,
  );
  return column <= 16_384 && Number(match[2]) <= 1_048_576;
}

const SpreadsheetScalarSchema = z.union([
  z.string().max(32_767),
  z.number().finite().min(-1e15).max(1e15),
  z.boolean(),
  z.null(),
]);

const SpreadsheetCellSchema = z.object({ value: SpreadsheetScalarSchema }).strict();
const SpreadsheetColumnSchema = z.object({
  index: z.number().int().min(1).max(16_384),
  width: z.number().finite().min(20).max(1_000).default(120),
  hidden: z.boolean().default(false),
}).strict();
const SpreadsheetSheetSchema = z.object({
  id: boundedId,
  name: z.string().trim().min(1).max(100).refine((value) => !CONTROL_OR_FORMAT_CHARACTER.test(value)),
  cells: z.record(z.string(), SpreadsheetCellSchema).default({}),
  columns: z.array(SpreadsheetColumnSchema).max(16_384).default([]),
}).strict().superRefine((sheet, context) => {
  Object.keys(sheet.cells).forEach((address) => {
    if (!validXlsxAddress(address)) {
      context.addIssue({ code: 'custom', path: ['cells', address], message: 'Cell address is outside XFD1048576.' });
    }
  });
  const indexes = sheet.columns.map((column) => column.index);
  if (new Set(indexes).size !== indexes.length) {
    context.addIssue({ code: 'custom', path: ['columns'], message: 'Column indexes must be unique.' });
  }
});

export const SpreadsheetArtifactContentSchema = z.object({
  kind: z.literal('spreadsheet'),
  schemaVersion: z.literal(2),
  calculationMode: z.literal('disabled'),
  sheets: z.array(SpreadsheetSheetSchema).min(1).max(1_024),
}).strict().superRefine((workbook, context) => {
  const ids = workbook.sheets.map((sheet) => sheet.id);
  if (new Set(ids).size !== ids.length) {
    context.addIssue({ code: 'custom', path: ['sheets'], message: 'Sheet IDs must be unique.' });
  }
  const cellCount = workbook.sheets.reduce((count, sheet) => count + Object.keys(sheet.cells).length, 0);
  if (cellCount > 100_000) {
    context.addIssue({ code: 'custom', path: ['sheets'], message: 'Workbook exceeds 100000 cells.' });
  }
});

const LegacySpreadsheetArtifactContentSchema = z.object({
  kind: z.literal('spreadsheet'),
  schemaVersion: z.literal(1),
}).passthrough();

const CanvasObjectSchema = z.object({
  id: boundedId,
  type: z.enum(['rectangle', 'ellipse', 'text', 'line', 'arrow', 'note', 'image']),
  x: z.number().finite().min(-1_000_000).max(1_000_000),
  y: z.number().finite().min(-1_000_000).max(1_000_000),
  width: z.number().finite().positive().max(1_000_000),
  height: z.number().finite().positive().max(1_000_000),
  text: z.string().max(10_000).nullable().optional(),
  assetId: boundedId.nullable().optional(),
}).strict().superRefine((item, context) => {
  if (item.type === 'image' && !item.assetId) {
    context.addIssue({ code: 'custom', path: ['assetId'], message: 'Canvas image requires an asset ID.' });
  }
  if (item.type !== 'image' && item.assetId) {
    context.addIssue({ code: 'custom', path: ['assetId'], message: 'Only images may reference assets.' });
  }
});

export const CanvasArtifactContentSchema = z.object({
  kind: z.literal('canvas'),
  schemaVersion: z.literal(2),
  snapshot: z.object({ objects: z.array(CanvasObjectSchema).max(10_000).default([]) }).strict(),
  assetIds: z.array(boundedId).max(10_000).default([]),
  embeds: z.literal('deny'),
  remoteAssets: z.literal('deny'),
}).strict().superRefine((canvas, context) => {
  const objectIds = canvas.snapshot.objects.map((item) => item.id);
  if (new Set(objectIds).size !== objectIds.length) {
    context.addIssue({ code: 'custom', path: ['snapshot', 'objects'], message: 'Canvas object IDs must be unique.' });
  }
  const assets = new Set(canvas.assetIds);
  if (assets.size !== canvas.assetIds.length) {
    context.addIssue({ code: 'custom', path: ['assetIds'], message: 'Canvas asset IDs must be unique.' });
  }
  canvas.snapshot.objects.forEach((item, index) => {
    if (item.assetId && !assets.has(item.assetId)) {
      context.addIssue({ code: 'custom', path: ['snapshot', 'objects', index, 'assetId'], message: 'Unknown canvas asset ID.' });
    }
  });
});

const LegacyCanvasArtifactContentSchema = z.object({
  kind: z.literal('canvas'),
  schemaVersion: z.literal(1),
}).passthrough();

const LegacyCanvasArtifactExportContentSchema = z.object({
  kind: z.literal('canvas'),
  schemaVersion: z.literal(1),
  snapshot: z.record(z.string(), z.json()),
  assetIds: z.array(boundedId).max(10_000).default([]),
  embeds: z.literal('deny').default('deny'),
  remoteAssets: z.literal('deny').default('deny'),
}).strict();

export const CanvasArtifactExportContentSchema = z.union([
  CanvasArtifactContentSchema,
  LegacyCanvasArtifactExportContentSchema,
]);

const NonCodeArtifactContentSchema = z
  .object({
    kind: z.enum(['document', 'form', 'slides']),
    schemaVersion: z.number().int().min(1).max(1000),
  })
  .passthrough();

export const ArtifactContentSchema = z.union([
  CodeArtifactContentSchema,
  LegacyCodeArtifactContentSchema,
  FlowArtifactContentSchema,
  LegacyFlowArtifactContentSchema,
  SpreadsheetArtifactContentSchema,
  LegacySpreadsheetArtifactContentSchema,
  CanvasArtifactContentSchema,
  LegacyCanvasArtifactContentSchema,
  NonCodeArtifactContentSchema,
]);

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
    if (value.revision.schemaVersion !== value.content.schemaVersion) {
      context.addIssue({ code: 'custom', path: ['revision', 'schemaVersion'], message: 'Revision content schema mismatch.' });
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

export const ArtifactFormSubmissionResultSchema = z
  .object({
    submissionId: boundedId,
    artifactId: boundedId,
    schemaRevisionId: boundedId,
    status: z.enum(['accepted', 'pending_continuation']),
    responseSha256: sha256,
    continuationAction: z.enum(['none', 'require_approval']),
    approvalId: boundedId.nullable(),
    reasonCode: z.enum(['FORM_CONTINUATION_NOT_REQUIRED', 'FORM_CONTINUATION_APPROVAL_REQUIRED']),
    actionHash: sha256.nullable(),
    disposition: z.enum(['created', 'idempotent_replay']),
  })
  .strict()
  .superRefine((value, context) => {
    const pending = value.status === 'pending_continuation';
    if (pending !== (value.continuationAction === 'require_approval')) {
      context.addIssue({ code: 'custom', path: ['continuationAction'], message: 'Continuation status mismatch.' });
    }
    if (pending !== (value.approvalId !== null && value.actionHash !== null)) {
      context.addIssue({ code: 'custom', path: ['approvalId'], message: 'Approval binding mismatch.' });
    }
    const expectedReason = pending ? 'FORM_CONTINUATION_APPROVAL_REQUIRED' : 'FORM_CONTINUATION_NOT_REQUIRED';
    if (value.reasonCode !== expectedReason) {
      context.addIssue({ code: 'custom', path: ['reasonCode'], message: 'Continuation reason mismatch.' });
    }
  });

export type ArtifactKind = z.infer<typeof ArtifactKindSchema>;
export type ArtifactStatus = z.infer<typeof ArtifactStatusSchema>;
export type ArtifactDataClass = z.infer<typeof ArtifactDataClassSchema>;
export type ArtifactMutationType = z.infer<typeof ArtifactMutationTypeSchema>;
export type ArtifactDescriptor = z.infer<typeof ArtifactDescriptorSchema>;
export type ArtifactRevision = z.infer<typeof ArtifactRevisionSchema>;
export type ArtifactContent = z.infer<typeof ArtifactContentSchema>;
export type CodeArtifactLanguage = z.infer<typeof CodeArtifactLanguageSchema>;
export type CodeArtifactContent = z.output<typeof CodeArtifactContentSchema>;
export type ArtifactLicenseCapability = z.output<typeof ArtifactLicenseCapabilitySchema>;
export type FlowArtifactContent = z.output<typeof FlowArtifactContentSchema>;
export type SpreadsheetArtifactContent = z.output<typeof SpreadsheetArtifactContentSchema>;
export type CanvasArtifactContent = z.output<typeof CanvasArtifactContentSchema>;
export type ArtifactReadResult = z.infer<typeof ArtifactReadResultSchema>;
export type ArtifactOperationResult = z.infer<typeof ArtifactOperationResultSchema>;
export type ArtifactMutationProposalResult = z.output<typeof ArtifactMutationProposalResultSchema>;
export type ArtifactListResult = z.output<typeof ArtifactListWireSchema>;
export type ArtifactHistoryResult = z.output<typeof ArtifactHistoryWireSchema>;
export type ArtifactExportBeginResult = z.infer<typeof ArtifactExportBeginResultSchema>;
export type ArtifactExportResult = z.infer<typeof ArtifactExportResultSchema>;
export type ArtifactFormSubmissionResult = z.infer<typeof ArtifactFormSubmissionResultSchema>;

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

export type SpreadsheetCellOperation =
  | { op: 'set'; address: string; value: string | number | boolean | null }
  | { op: 'clear'; address: string };

export interface SpreadsheetCellPatchRequest {
  artifactId: string;
  expectedRevisionNumber: number;
  sheetId: string;
  operations: SpreadsheetCellOperation[];
  idempotencyKey: string;
  changeSummary?: string;
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
  sourceRevisionId: string;
  artifactId?: string;
  title: string;
  contentOverride?: ArtifactContent;
  idempotencyKey: string;
}

export interface ArtifactFormSubmissionRequest {
  artifactId: string;
  schemaRevisionId: string;
  response: Record<string, unknown>;
  persistencePolicy: 'none';
  idempotencyKey: string;
}

export interface ArtifactExportBeginRequest {
  artifactId: string;
  revisionId: string;
  format: 'source' | 'zip' | 'json' | 'markdown' | 'html' | 'svg' | 'png' | 'csv' | 'xlsx' | 'pptx';
  idempotencyKey: string;
}
