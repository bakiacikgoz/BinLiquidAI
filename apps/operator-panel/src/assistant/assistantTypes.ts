export type AssistantTurnStatus =
  | 'idle'
  | 'starting'
  | 'streaming'
  | 'awaiting_approval'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type AssistantStreamEventType =
  | 'status'
  | 'token'
  | 'router_decision'
  | 'policy_decision'
  | 'approval_pending'
  | 'expert_start'
  | 'expert_end'
  | 'audit_artifact'
  | 'final'
  | 'warning'
  | 'error'
  | 'cancelled';

export interface AssistantStartTurnOptions {
  assistantTurnId: string;
  sessionId: string;
  userMessage: string;
  compiledPrompt: string;
  profile?: string;
  provider?: string;
  providerId?: string;
  fallbackProvider?: string;
  fallbackProviderId?: string;
  model?: string;
  hfModelId?: string;
  dataClassHint?: 'public' | 'internal' | 'confidential' | 'regulated';
}

export type AssistantContextAttachmentKind =
  | 'active_run'
  | 'event_tail'
  | 'approval_summary'
  | 'artifact_summary'
  | 'system_health';

export type AssistantSafeToolIntent =
  | 'inspect_run'
  | 'summarize_events'
  | 'explain_policy_blocker'
  | 'draft_remediation_plan'
  | 'prepare_approval_review';

export interface AssistantComposerControls {
  contextAttachmentKinds: AssistantContextAttachmentKind[];
  toolIntents: AssistantSafeToolIntent[];
}

export interface AssistantStartTurnResponse {
  contractVersion: string;
  assistantTurnId: string;
  sessionId: string;
  processId: number | null;
  status: 'started';
}

export interface AssistantCancelTurnResponse {
  contractVersion: string;
  assistantTurnId: string;
  sessionId: string;
  processId: number | null;
  status: 'cancelled';
}

export interface AssistantStreamEvent {
  contractVersion: string;
  assistantTurnId: string;
  sessionId: string;
  event: AssistantStreamEventType;
  sequence: number;
  timestampUtc: string;
  data: unknown;
}

export interface AssistantUiError {
  code: string;
  message: string;
  retryable: boolean;
  stderrPreview?: string;
}

export interface AssistantUserMessage {
  id: string;
  text: string;
  createdAtUtc: string;
}

export interface AssistantTimelineItem {
  id: string;
  tone: 'info' | 'success' | 'warning' | 'error';
  title: string;
  subtitle: string;
  timestampUtc: string;
}

export interface AssistantFinding {
  id: string;
  tone: 'info' | 'success' | 'warning' | 'error';
  title: string;
  body: string;
}

export interface AssistantRunRef {
  id: string;
  status?: string;
  summary?: string;
}

export interface AssistantArtifactRef {
  name: string;
  path?: string;
  summary?: string;
}

export interface AssistantProposedAction {
  id: string;
  title: string;
  target: string;
  risk: 'low' | 'medium' | 'high';
  dryRunSummary: string;
  commandPreview?: string;
}

export interface AssistantApprovalSummary {
  approvalId: string;
  title: string;
  status: string;
  risk: 'low' | 'medium' | 'high';
  detailLoaded: boolean;
  detail?: unknown;
}

export interface AssistantMetrics {
  traceId?: string;
  usedPath?: string;
  fallbackEvents?: string[];
}

export interface AssistantAssistantMessage {
  id: string;
  text: string;
  findings: AssistantFinding[];
  timeline: AssistantTimelineItem[];
  proposedAction: AssistantProposedAction | null;
  approval: AssistantApprovalSummary | null;
  referencedRuns: AssistantRunRef[];
  referencedArtifacts: AssistantArtifactRef[];
  metrics: AssistantMetrics | null;
  warning: string | null;
  error: AssistantUiError | null;
}

export interface AssistantTurn {
  id: string;
  userMessage: AssistantUserMessage;
  assistantMessage: AssistantAssistantMessage;
  composerControls: AssistantComposerControls | null;
  startedAtUtc: string;
  completedAtUtc: string | null;
  status: AssistantTurnStatus;
  eventSequence: number;
}

export interface AssistantSessionState {
  sessionId: string;
  turns: AssistantTurn[];
  activeTurnId: string | null;
  status: AssistantTurnStatus;
  selectedRunIds: string[];
  referencedArtifacts: AssistantArtifactRef[];
  pendingApprovalId: string | null;
  error: AssistantUiError | null;
}

export interface AssistantPromptBuildResult {
  compiledPrompt: string;
  characterCount: number;
  truncated: boolean;
  omittedSections: string[];
}

export type AssistantFixtureScenario = 'welcome' | 'running' | 'approval_required';
