import type {
  AssistantTaskAgentCandidate,
  AssistantTaskEvidenceExpectation,
  AssistantTaskPlan,
  AssistantTaskPlanStatus,
  AssistantTaskPolicyDecision,
  AssistantTaskPolicyPreview,
  AssistantTaskRiskClass,
  AssistantTaskSubmissionResult,
  AssistantTaskSubmitStatus,
} from './assistantTaskingTypes';

type RecordValue = Record<string, unknown>;

function asRecord(value: unknown): RecordValue {
  return typeof value === 'object' && value !== null ? (value as RecordValue) : {};
}

function readString(source: RecordValue, key: string, fallback = ''): string {
  const value = source[key];
  return typeof value === 'string' ? value : fallback;
}

function readNullableString(source: RecordValue, key: string): string | null {
  const value = source[key];
  return typeof value === 'string' && value.trim() ? value : null;
}

function readBoolean(source: RecordValue, key: string, fallback = false): boolean {
  const value = source[key];
  return typeof value === 'boolean' ? value : fallback;
}

function readStringArray(source: RecordValue, key: string): string[] {
  const value = source[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

function readEnum<T extends string>(source: RecordValue, key: string, allowed: readonly T[], fallback: T): T {
  const value = source[key];
  return typeof value === 'string' && allowed.includes(value as T) ? (value as T) : fallback;
}

const RISK_CLASSES = [
  'read_only',
  'external_write',
  'mutation',
  'destructive',
  'credential_sensitive',
  'unknown',
] as const satisfies readonly AssistantTaskRiskClass[];

const POLICY_DECISIONS = ['allow', 'require_approval', 'deny', 'unknown'] as const satisfies readonly AssistantTaskPolicyDecision[];

const PLAN_STATUSES = ['planned', 'blocked', 'clarification_required'] as const satisfies readonly AssistantTaskPlanStatus[];

const SUBMIT_STATUSES = [
  'accepted',
  'blocked_pending_approval',
  'denied',
  'invalid_request',
  'unknown_agent',
] as const satisfies readonly AssistantTaskSubmitStatus[];

export function normalizeAssistantTaskAgentCandidate(value: unknown): AssistantTaskAgentCandidate {
  const record = asRecord(value);
  const agentId = readString(record, 'agentId', 'unknown-agent');
  return {
    agentId,
    label: readString(record, 'label', agentId),
    enrolled: readBoolean(record, 'enrolled'),
    workspaceId: readNullableString(record, 'workspaceId'),
    principalId: readNullableString(record, 'principalId'),
    allowedSurfaces: readStringArray(record, 'allowedSurfaces'),
    blockedSurfaces: readStringArray(record, 'blockedSurfaces'),
    declaredActions: readStringArray(record, 'declaredActions'),
    qualificationStatus: readString(record, 'qualificationStatus', 'unknown'),
    blockingReasons: readStringArray(record, 'blockingReasons'),
  };
}

export function normalizeAssistantTaskPolicyPreview(value: unknown): AssistantTaskPolicyPreview {
  const record = asRecord(value);
  return {
    decision: readEnum(record, 'decision', POLICY_DECISIONS, 'unknown'),
    riskClass: readEnum(record, 'riskClass', RISK_CLASSES, 'unknown'),
    approvalRequired: readBoolean(record, 'approvalRequired'),
    safeToSubmit: readBoolean(record, 'safeToSubmit'),
    reasonCode: readString(record, 'reasonCode', 'ASSISTANT_TASK_POLICY_UNKNOWN'),
    blockedReasons: readStringArray(record, 'blockedReasons'),
  };
}

function normalizeEvidenceExpectation(value: unknown): AssistantTaskEvidenceExpectation {
  const record = asRecord(value);
  return {
    mode: 'hash_only_redacted',
    expectedRefs: readStringArray(record, 'expectedRefs'),
    rawContentPersisted: readBoolean(record, 'rawContentPersisted'),
  };
}

export function normalizeAssistantTaskPlan(value: unknown): AssistantTaskPlan {
  const record = asRecord(value);
  const candidateAgents = Array.isArray(record.candidateAgents)
    ? record.candidateAgents.map(normalizeAssistantTaskAgentCandidate)
    : [];
  const selectedAgent = record.selectedAgent ? normalizeAssistantTaskAgentCandidate(record.selectedAgent) : null;
  const policyPreview = normalizeAssistantTaskPolicyPreview(record.policyPreview);
  return {
    schemaVersion: 'assistant-tasking.plan/v1',
    proposalId: readString(record, 'proposalId', 'unknown-proposal'),
    planHash: readString(record, 'planHash'),
    status: readEnum(record, 'status', PLAN_STATUSES, 'blocked'),
    intentKind: readString(record, 'intentKind', 'clarification_required'),
    selectedAgent,
    candidateAgents,
    taskSummary: readString(record, 'taskSummary', 'No task summary was provided.'),
    riskClass: readEnum(record, 'riskClass', RISK_CLASSES, policyPreview.riskClass),
    policyPreview,
    approvalRequired: readBoolean(record, 'approvalRequired', policyPreview.approvalRequired),
    submitMode:
      readString(record, 'submitMode') === 'proposal_first' ? 'proposal_first' : 'disabled_with_reason',
    idempotencyKey: readString(record, 'idempotencyKey'),
    evidenceExpectation: normalizeEvidenceExpectation(record.evidenceExpectation),
    safeToSubmit: readBoolean(record, 'safeToSubmit', policyPreview.safeToSubmit),
    blockedReasons: readStringArray(record, 'blockedReasons'),
    sourceRefs: readStringArray(record, 'sourceRefs'),
    createdAtUtc: readString(record, 'createdAtUtc'),
  };
}

export function normalizeAssistantTaskSubmissionResult(value: unknown): AssistantTaskSubmissionResult {
  const record = asRecord(value);
  return {
    schemaVersion: 'assistant-tasking.submission/v1',
    proposalId: readString(record, 'proposalId', 'unknown-proposal'),
    planHash: readString(record, 'planHash'),
    status: readEnum(record, 'status', SUBMIT_STATUSES, 'invalid_request'),
    policyDecision: readEnum(record, 'policyDecision', POLICY_DECISIONS, 'unknown'),
    reasonCode: readString(record, 'reasonCode', 'ASSISTANT_TASK_SUBMISSION_UNKNOWN'),
    runId: readNullableString(record, 'runId'),
    approvalId: readNullableString(record, 'approvalId'),
    evidenceRef: readNullableString(record, 'evidenceRef'),
    replayStatus: readNullableString(record, 'replayStatus'),
    idempotencyStatus: readNullableString(record, 'idempotencyStatus'),
    blockedReasons: readStringArray(record, 'blockedReasons'),
    nextActions: readStringArray(record, 'nextActions'),
    generatedAtUtc: readString(record, 'generatedAtUtc'),
  };
}
