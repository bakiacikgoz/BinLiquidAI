export type AssistantTaskRiskClass =
  | 'read_only'
  | 'external_write'
  | 'mutation'
  | 'destructive'
  | 'credential_sensitive'
  | 'unknown';

export type AssistantTaskPolicyDecision = 'allow' | 'require_approval' | 'deny' | 'unknown';

export type AssistantTaskPlanStatus = 'planned' | 'blocked' | 'clarification_required';

export type AssistantTaskSubmitStatus =
  | 'accepted'
  | 'blocked_pending_approval'
  | 'denied'
  | 'invalid_request'
  | 'unknown_agent';

export interface AssistantTaskAgentCandidate {
  agentId: string;
  label: string;
  enrolled: boolean;
  workspaceId: string | null;
  principalId: string | null;
  allowedSurfaces: string[];
  blockedSurfaces: string[];
  declaredActions: string[];
  qualificationStatus: string;
  blockingReasons: string[];
}

export interface AssistantTaskPolicyPreview {
  decision: AssistantTaskPolicyDecision;
  riskClass: AssistantTaskRiskClass;
  approvalRequired: boolean;
  safeToSubmit: boolean;
  reasonCode: string;
  blockedReasons: string[];
}

export interface AssistantTaskEvidenceExpectation {
  mode: 'hash_only_redacted';
  expectedRefs: string[];
  rawContentPersisted: boolean;
}

export interface AssistantTaskPlan {
  schemaVersion: 'assistant-tasking.plan/v1';
  proposalId: string;
  planHash: string;
  status: AssistantTaskPlanStatus;
  intentKind: string;
  selectedAgent: AssistantTaskAgentCandidate | null;
  candidateAgents: AssistantTaskAgentCandidate[];
  taskSummary: string;
  riskClass: AssistantTaskRiskClass;
  policyPreview: AssistantTaskPolicyPreview;
  approvalRequired: boolean;
  submitMode: 'proposal_first' | 'disabled_with_reason';
  idempotencyKey: string;
  evidenceExpectation: AssistantTaskEvidenceExpectation;
  safeToSubmit: boolean;
  blockedReasons: string[];
  sourceRefs: string[];
  createdAtUtc: string;
}

export interface AssistantTaskSubmissionResult {
  schemaVersion: 'assistant-tasking.submission/v1';
  proposalId: string;
  planHash: string;
  status: AssistantTaskSubmitStatus;
  policyDecision: AssistantTaskPolicyDecision;
  reasonCode: string;
  runId: string | null;
  approvalId: string | null;
  evidenceRef: string | null;
  replayStatus: string | null;
  idempotencyStatus: string | null;
  blockedReasons: string[];
  nextActions: string[];
  generatedAtUtc: string;
}
