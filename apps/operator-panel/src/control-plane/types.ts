export type DataSourceMode = 'preview_fixture' | 'tauri_live' | 'cli_live' | 'stale_cache' | 'error';
export type DataFreshness = 'fresh' | 'stale' | 'unknown';
export type HealthStatus = 'healthy' | 'partial' | 'degraded' | 'blocked' | 'unknown';
export type SurfaceStatus = 'ready' | 'conditional' | 'blocked' | 'not_applicable';

export interface DataSourceState {
  mode: DataSourceMode;
  isMock: boolean;
  isSilentFallback: boolean;
  lastRefreshUtc: string | null;
  ageMs: number | null;
  freshness: DataFreshness;
  contractVersion: string;
  sourceReason?: string | null;
}

export interface SystemHealthState {
  status: HealthStatus;
  confidence: 'high' | 'medium' | 'low';
  missingSignals: string[];
  blockingReasons: string[];
  lastDoctorStatus: string;
  humanSummary: string;
}

export interface SystemSummary {
  profile: string;
  rootDir: string;
  coreVersion: string;
  contractVersion: string;
  health: SystemHealthState;
  doctor: Record<string, unknown>;
  capabilities: Record<string, unknown>;
  configSummary: Record<string, unknown>;
  sourceMap: Record<string, string>;
  warnings: string[];
}

export interface DashboardSummary {
  agentCount: number;
  runCount: number;
  pendingApprovalCount: number;
  evidencePackCount: number;
  activeAlertCount: number;
  blockedClaimCount: number;
  conditionalClaimCount: number;
}

export interface AgentSummary {
  agentId: string;
  displayName: string;
  runtimeKind: string;
  agentType: 'internal' | 'external_stdio' | 'external_http' | 'computer_use_adapter';
  status: string;
  readiness: string;
  ownerTeam?: string | null;
  policyPackId?: string | null;
  riskProfile: 'read_only' | 'guarded' | 'restricted' | 'blocked';
  lastRunId?: string | null;
  lastEvidencePackId?: string | null;
  lastEvidenceStatus: 'missing' | 'pending' | 'valid' | 'invalid';
}

export interface RunSnapshotSummary {
  runId: string;
  agentId: string;
  profile: string;
  status: string;
  submittedBy: string;
  identityRef?: string | null;
  inputHash: string;
  policyHash: string;
  startedAt: string;
  completedAt?: string | null;
  approvalIds: string[];
  artifactRefs: string[];
  evidencePackId?: string | null;
  blockingReasons: string[];
  nextActions: string[];
}

export interface ApprovalSnapshotSummary {
  approvalId: string;
  runId: string;
  status: string;
  targetKind: string;
  targetRef: string;
  actionHash: string;
  policyHash: string;
  requestHash: string;
  snapshotHash: string;
  executionStatus: string;
  createdAt: string;
  expiresAt: string;
  actor?: string | null;
  disabledReason?: string | null;
}

export interface EvidencePackSummary {
  packId: string;
  runId?: string | null;
  createdAtUtc?: string | null;
  signatureStatus: 'missing' | 'pending' | 'valid' | 'invalid';
  hashChainStatus: 'pending' | 'valid' | 'broken';
  replayStatus: 'not_available' | 'pending' | 'passed' | 'failed';
  claimGuardStatus: 'ready' | 'conditional' | 'blocked';
  redactionStatus: 'passed' | 'warning' | 'failed' | 'unknown';
  artifactCount: number;
  exportPath?: string | null;
  blockingReasons: string[];
}

export interface PolicyPackSummary {
  packId: string;
  label: string;
  version: string;
  status: 'active' | 'available' | 'missing' | 'blocked';
  policyHash?: string | null;
  ruleCount: number;
  sourcePath?: string | null;
  blockingReasons: string[];
}

export interface ExecutionSurfaceSummary {
  surfaceId: string;
  label: string;
  status: SurfaceStatus;
  claimId?: string | null;
  reasonCodes: string[];
  humanSummary: string;
}

export interface LogEventSummary {
  eventId: string;
  timestamp: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  source: string;
  message: string;
  runId?: string | null;
  evidencePackId?: string | null;
}

export interface AlertSummary {
  alertId: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  status: 'active' | 'resolved';
  title: string;
  reasonCode: string;
  recommendedAction: string;
  linkedRunId?: string | null;
  linkedEvidencePackId?: string | null;
}

export interface ReportSummary {
  reportId: string;
  kind: 'readiness' | 'evidence' | 'qualification' | 'support' | 'security' | 'metrics';
  title: string;
  status: 'ready' | 'conditional' | 'blocked' | 'missing';
  path?: string | null;
  generatedAtUtc?: string | null;
  blockingReasons: string[];
}

export interface OperationResultSummary {
  status: 'not_run' | 'passed' | 'failed' | 'blocked';
  summary: string;
  generatedAtUtc?: string | null;
  errorCode?: string | null;
}

export interface OperationDescriptor {
  operationId: string;
  category: 'identity' | 'qualification' | 'security' | 'keys' | 'support' | 'backup' | 'restore' | 'migration';
  label: string;
  description: string;
  riskLevel: 'read_only' | 'low' | 'medium' | 'high' | 'destructive';
  permission: string;
  supportsDryRun: boolean;
  enabled: boolean;
  disabledReason?: string | null;
  lastResult?: OperationResultSummary | null;
}

export interface UserSummary {
  userId: string;
  subject: string;
  issuer?: string | null;
  status: 'active' | 'expired' | 'unknown';
  roles: string[];
  permissions: string[];
  lastSeenUtc?: string | null;
}

export interface RoleSummary {
  roleId: string;
  label: string;
  riskLevel: 'low' | 'medium' | 'high';
  permissions: string[];
  assignmentCount: number;
}

export interface AdminSummary {
  users: UserSummary[];
  roles: RoleSummary[];
  policyPacks: PolicyPackSummary[];
  permissionMatrix: Record<string, string[]>;
  source: 'local_fixture' | 'identity_assertion' | 'external_idp_placeholder';
}

export interface QuickActionSummary {
  actionId: string;
  label: string;
  enabled: boolean;
  disabledReason?: string | null;
}

export interface DesignPartnerRcCheck {
  checkId: string;
  label: string;
  status: 'passed' | 'conditional' | 'failed';
  detail: string;
  blocking: boolean;
}

export interface DesignPartnerRcStatus {
  schemaVersion: 'control-plane.design-partner-rc/v1';
  generatedAtUtc: string;
  status: 'ready' | 'conditional' | 'blocked';
  checks: DesignPartnerRcCheck[];
  blockers: string[];
  warnings: string[];
  artifactRoot: string;
}

export interface PilotLaunchStatusTile {
  tileId: string;
  label: string;
  status: 'ready' | 'conditional' | 'blocked' | 'missing';
  detail: string;
  path?: string | null;
  blockingReasons: string[];
}

export interface PilotLaunchNextAction {
  label: string;
  severity: 'info' | 'warning' | 'blocking';
  target: string;
}

export interface PilotLaunchAdminProposalSummary {
  proposalId: string;
  kind: string;
  operation: string;
  status: string;
  permissionRequired: string;
  approvalId?: string | null;
  auditEnvelopePath?: string | null;
}

export interface PilotLaunchReadinessStatus {
  schemaVersion: 'control-plane.pilot-launch-readiness/v1';
  generatedAtUtc: string;
  status: 'ready' | 'conditional' | 'blocked';
  headline: string;
  artifactRoot: string;
  enterpriseHatA: PilotLaunchStatusTile;
  installRehearsal: PilotLaunchStatusTile;
  externalAgentPilot: PilotLaunchStatusTile;
  governanceAdmin: PilotLaunchStatusTile;
  securityReview: PilotLaunchStatusTile;
  claimGuard: PilotLaunchStatusTile;
  evidenceCorpus: PilotLaunchStatusTile;
  pilotMetrics: PilotLaunchStatusTile;
  adminProposals: PilotLaunchAdminProposalSummary[];
  nextActions: PilotLaunchNextAction[];
  blockers: string[];
  warnings: string[];
}

export interface CodeIntelligenceFindingBucket {
  bucketId: string;
  label: string;
  status: 'ready' | 'warn' | 'blocked' | 'missing';
  count: number;
  errors: number;
  warnings: number;
  path?: string | null;
  detail: string;
}

export interface CodeIntelligenceSummary {
  schemaVersion: 'control-plane.code-intelligence-summary/v1';
  generatedAtUtc: string;
  status: 'ready' | 'conditional' | 'blocked' | 'missing';
  verdict: string;
  tool: string;
  toolVersion?: string | null;
  artifactRoot: string;
  telemetryDisabled: boolean;
  boundaryViolations: number;
  secretScanStatus: string;
  buckets: CodeIntelligenceFindingBucket[];
  blockers: string[];
  warnings: string[];
}

export interface PilotOperationsChecklistItem {
  itemId: string;
  label: string;
  status: 'ready' | 'conditional' | 'blocked' | 'missing';
  detail: string;
  path?: string | null;
  blocking: boolean;
}

export interface PilotOperationsTimelineEvent {
  eventId: string;
  label: string;
  status: 'completed' | 'pending' | 'blocked' | 'warning';
  detail: string;
  artifactRef?: string | null;
  occurredAtUtc?: string | null;
}

export interface PilotOperationsStatus {
  schemaVersion: 'control-plane.pilot-operations/v1';
  generatedAtUtc: string;
  status: 'ready' | 'conditional' | 'blocked';
  headline: string;
  artifactRoot: string;
  checklist: PilotOperationsChecklistItem[];
  timeline: PilotOperationsTimelineEvent[];
  acceptanceMetrics: Record<string, unknown>;
  feedbackBundlePath?: string | null;
  nextActions: PilotLaunchNextAction[];
  blockers: string[];
  warnings: string[];
}

export interface DesignPartnerBetaStatus {
  schemaVersion: 'control-plane.design-partner-beta/v1';
  generatedAtUtc: string;
  status: 'ready' | 'conditional' | 'blocked';
  headline: string;
  artifactRoot: string;
  codeIntelligence: CodeIntelligenceSummary;
  pilotOperations: PilotOperationsStatus;
  checks: PilotOperationsChecklistItem[];
  blockers: string[];
  warnings: string[];
}

export interface ProviderRegistryEntry {
  providerKind:
    | 'ollama'
    | 'transformers'
    | 'openai_responses'
    | 'anthropic_messages'
    | 'google_gemini'
    | 'deepseek_chat';
  displayName: string;
  status: 'available' | 'blocked' | 'conditional' | 'canary_only';
  credentialState: 'missing' | 'configured' | 'not_required' | 'redacted';
  canaryOnly: boolean;
  supportsStreaming: boolean;
  serverToolsPolicy: 'denied' | 'approval_required';
  customToolsPolicy: 'proposal_only' | 'approval_required' | 'execute';
  retentionPolicy: 'hash_only_store_false';
  lastConformanceStatus?: 'pass' | 'fail' | 'unknown' | null;
  blockingReasons: string[];
}

export interface ProviderGovernanceSnapshot {
  contractVersion: 'control-plane.provider-governance/v1';
  generatedAtUtc: string;
  providers: ProviderRegistryEntry[];
  overallStatus: 'ready' | 'conditional' | 'blocked';
  blockingReasons: string[];
}

export interface ProviderInvocationArtifact {
  schemaVersion: 'provider.invocation.v1';
  status: 'pass' | 'blocked' | 'conditional' | 'error';
  invocationId: string;
  providerKind: string;
  model: string;
  runtimeMode: 'offline_conformance' | 'dry_run' | 'canary_live' | 'disabled';
  policyDecision: Record<string, unknown>;
  requestHash: string;
  responseHash?: string | null;
  rawPersistence: false;
  evidenceMode: 'hash_only';
  toolPolicy: {
    serverToolsPolicy: 'denied' | 'approval_required';
    customToolsPolicy: 'proposal_only' | 'approval_required' | 'execute';
    requestedServerTools: string[];
  };
  blockingReasons: string[];
  createdAtUtc: string;
}

export interface ProviderWorkflowProofArtifact {
  schemaVersion: 'provider.workflow-proof.v1';
  status: 'pass' | 'conditional' | 'blocked' | 'error';
  workflowId: string;
  workflowKind: 'read_only_ops_triage';
  agentId: string;
  providerInvocations: string[];
  proposals: Array<{
    proposalId: string;
    actionId: string;
    riskClass: 'read_only' | 'mutation' | 'destructive';
    executionMode: 'proposal_only';
    effectSummary: string;
  }>;
  executedMutations: number;
  approvalTicketsCreated: number;
  evidenceArtifacts: string[];
  blockingReasons: string[];
  generatedAtUtc: string;
}

export interface ProviderRuntimeSnapshot {
  contractVersion: 'control-plane.provider-runtime/v1';
  generatedAtUtc: string;
  enabled: boolean;
  latestInvocations: ProviderInvocationArtifact[];
  workflowProofs: ProviderWorkflowProofArtifact[];
  blockingReasons: string[];
}

export interface TargetEvidenceClosureSummary {
  contractVersion: 'control-plane.target-evidence-closure/v1';
  generatedAtUtc: string;
  status: 'pass' | 'conditional' | 'blocked' | 'unknown';
  sessionId?: string | null;
  mode?: 'rehearsal' | 'target' | null;
  evidenceMode?: 'hash_only' | null;
  rawPersistence: false;
  blockingReasons: string[];
  warnings: string[];
  blockedClaims: string[];
  attestationStatus: 'missing' | 'present' | 'signed' | 'invalid';
}

export interface MemoryAuthorityRecordsSummary {
  active: number;
  expired: number;
  tombstoned: number;
  deniedWrites: number;
  pendingProposals: number;
}

export interface MemoryScopeSummary {
  scope: string;
  visibility: string;
  activeRecords: number;
  policy: string;
}

export interface MemoryIndexStatus {
  backend: string;
  status: 'pass' | 'degraded' | 'disabled' | 'unavailable' | 'error';
  recordCount: number;
  lastRebuildAt?: string | null;
  degradedReason?: string | null;
  blockingReasons: string[];
  experimental: boolean;
}

export interface MemoryPrivacySummary {
  rawPromptPersistence: boolean;
  rawResponsePersistence: boolean;
  primaryUiRawContent: boolean;
}

export interface MemoryEvidenceSummary {
  mode: 'hash_only_redacted';
  lastArtifactRef?: string | null;
}

export interface MemoryAuthoritySnapshot {
  contractVersion: 'memory.authority-snapshot/v1';
  enabled: boolean;
  authorityStatus: 'pass' | 'disabled' | 'degraded' | 'blocked';
  storeSchemaVersion: 'memory.v3';
  records: MemoryAuthorityRecordsSummary;
  scopes: MemoryScopeSummary[];
  index: MemoryIndexStatus;
  privacy: MemoryPrivacySummary;
  evidence: MemoryEvidenceSummary;
  blockingReasons: string[];
  warnings: string[];
}

export interface ControlPlaneSnapshot {
  contractVersion: 'control-plane.snapshot/v1';
  generatedAtUtc: string;
  dataSource: DataSourceState;
  system: SystemSummary;
  dashboard: DashboardSummary;
  agents: AgentSummary[];
  runs: RunSnapshotSummary[];
  approvals: ApprovalSnapshotSummary[];
  evidencePacks: EvidencePackSummary[];
  policyPacks: PolicyPackSummary[];
  executionSurfaces: ExecutionSurfaceSummary[];
  logs: LogEventSummary[];
  alerts: AlertSummary[];
  reports: ReportSummary[];
  operations: OperationDescriptor[];
  admin: AdminSummary;
  designPartnerRc: DesignPartnerRcStatus;
  pilotLaunch: PilotLaunchReadinessStatus;
  codeIntelligence: CodeIntelligenceSummary;
  pilotOperations: PilotOperationsStatus;
  designPartnerBeta: DesignPartnerBetaStatus;
  providerGovernance: ProviderGovernanceSnapshot;
  providerRuntime: ProviderRuntimeSnapshot;
  targetEvidenceClosure: TargetEvidenceClosureSummary;
  memoryGovernance?: MemoryAuthoritySnapshot;
  quickActions: QuickActionSummary[];
  partialReasons: string[];
}

export interface UiError {
  code: string;
  message: string;
}

export interface EmptyState {
  title: string;
  detail: string;
}

export interface PageViewModel<TData> {
  pageId: string;
  title: string;
  subtitle?: string;
  dataSource: DataSourceState;
  loading: boolean;
  error?: UiError;
  empty?: EmptyState;
  data: TData;
  debug?: unknown;
}
