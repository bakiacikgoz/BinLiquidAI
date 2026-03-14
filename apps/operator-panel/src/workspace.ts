type JsonRecord = Record<string, unknown>;

export type WorkspaceStageKey =
  | 'planning'
  | 'reading_screen'
  | 'waiting_approval'
  | 'executing'
  | 'verifying'
  | 'blocked'
  | 'done';

export type WorkspaceRuntimeStateKey =
  | 'running'
  | 'awaiting_approval'
  | 'paused'
  | 'resuming'
  | 'stopping'
  | 'stopped'
  | 'completed'
  | 'failed'
  | 'recovered'
  | 'non_resumable';

export interface WorkspaceTranscriptEntry {
  id: string;
  role: 'user' | 'assistant' | 'system';
  title: string;
  body: string;
  pending?: boolean;
}

export interface WorkspaceTimelineEntry {
  id: string;
  event: string;
  timestamp: string;
  phase: string;
  summary: string;
  tone: 'neutral' | 'warning' | 'success';
}

export interface WorkspaceArtifactEntry {
  name: string;
  available: boolean;
  summary: string;
}

export interface WorkspaceLiveSurface {
  appIdentity: string;
  windowIdentity: string;
  targetRef: string;
  selector: string;
  riskClass: string;
  expectedEffect: string;
  approvalId: string | null;
}

export interface WorkspaceRuntimeState {
  displayState: WorkspaceRuntimeStateKey;
  rawState: string;
  registryState: string | null;
  activeSession: boolean;
  recoveryState: 'recovered' | 'non_resumable' | null;
  recoverySummary: string | null;
  controlHistoryCount: number;
  pendingApprovalId: string | null;
  pendingCommand: string | null;
  lastSafeCheckpoint: string | null;
  lastControlCommand: string | null;
  lastControlOutcome: string | null;
  lastControlReason: string | null;
  resumeAllowed: boolean;
  stoppedByUser: boolean;
  lastVerificationSummary: string | null;
  canPause: boolean;
  canResume: boolean;
  canStop: boolean;
}

export interface WorkspaceSnapshot {
  objective: string;
  stage: WorkspaceStageKey;
  progressIndex: number;
  progressTotal: number;
  currentStatus: string;
  blockedReason: string | null;
  liveSurface: WorkspaceLiveSurface | null;
  runtimeState: WorkspaceRuntimeState;
  transcript: WorkspaceTranscriptEntry[];
  timeline: WorkspaceTimelineEntry[];
  artifacts: WorkspaceArtifactEntry[];
}

const PROGRESS_STAGES: WorkspaceStageKey[] = [
  'planning',
  'reading_screen',
  'waiting_approval',
  'executing',
  'verifying',
  'done',
];

function asRecord(value: unknown): JsonRecord {
  return typeof value === 'object' && value !== null ? (value as JsonRecord) : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function readString(source: JsonRecord, key: string, fallback = ''): string {
  const value = source[key];
  return typeof value === 'string' ? value : fallback;
}

function readNullableString(source: JsonRecord, key: string): string | null {
  const value = source[key];
  return typeof value === 'string' && value.trim() ? value : null;
}

function readBool(source: JsonRecord, key: string): boolean {
  return source[key] === true;
}

function hasMeaningfulPayload(value: unknown): boolean {
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  if (typeof value === 'object' && value !== null) {
    return Object.keys(value).length > 0;
  }
  return value !== null && value !== undefined && value !== '';
}

function humanizeEvent(eventName: string): string {
  return eventName
    .replaceAll('.', ' ')
    .replaceAll('_', ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function humanizeValue(value: string | null): string {
  return value ? humanizeEvent(value) : 'Unknown';
}

function summarizeControlCommand(command: JsonRecord): string {
  return humanizeValue(readNullableString(command, 'command_type'));
}

function summarizeEvent(row: JsonRecord): string {
  const eventName = readString(row, 'event');
  const data = asRecord(row.data);
  if (eventName === 'team_start') {
    const request = readString(data, 'request');
    return request ? `Run accepted for "${request}".` : 'Run accepted.';
  }
  if (eventName === 'session_started') {
    return `Computer-use session started in ${readString(data, 'mode', 'execute')} mode.`;
  }
  if (eventName === 'observation_captured') {
    const url = readString(data, 'current_url');
    return url ? `Observed surface at ${url}.` : 'Observed current surface state.';
  }
  if (eventName === 'action_planned') {
    return `Planned ${readString(data, 'action_id', 'action')} on ${readString(data, 'selector', 'target')}.`;
  }
  if (eventName === 'action_started') {
    return `Executing ${readString(data, 'action_id', 'action')} on ${readString(data, 'selector', 'target')}.`;
  }
  if (eventName === 'action_verified') {
    return `Verified ${readString(data, 'action_id', 'action')} before continuing.`;
  }
  if (eventName === 'action_failed') {
    return `Action failed: ${readString(data, 'reason_code', readString(data, 'action_id', 'unknown_error'))}.`;
  }
  if (eventName === 'task_started') {
    const taskId = readString(row, 'task_id', 'task');
    return `${taskId} entered execution.`;
  }
  if (eventName === 'approval_requested') {
    return `Approval requested for ${readString(data, 'target', 'device action')}.`;
  }
  if (eventName === 'approval_required') {
    return `Approval required before ${readString(data, 'action_id', 'the next action')}.`;
  }
  if (eventName === 'computer_use.control_command_received') {
    return `${summarizeControlCommand(asRecord(data.command))} command received.`;
  }
  if (eventName === 'computer_use.control_command_rejected') {
    const command = asRecord(data.command);
    const result = asRecord(data.result);
    return `${summarizeControlCommand(command)} was rejected: ${readString(result, 'reason', 'state mismatch')}.`;
  }
  if (eventName === 'computer_use.pause_requested') {
    return 'Pause requested. Execution will stop at the next safe checkpoint.';
  }
  if (eventName === 'computer_use.paused') {
    return 'Task paused at a safe checkpoint.';
  }
  if (eventName === 'computer_use.resume_requested') {
    return 'Resume requested from the current checkpoint.';
  }
  if (eventName === 'computer_use.resumed') {
    return 'Task resumed from the last safe checkpoint.';
  }
  if (eventName === 'computer_use.stop_requested') {
    return 'Stop requested. Execution will end at the next safe checkpoint.';
  }
  if (eventName === 'computer_use.stopped') {
    return `Task stopped: ${readString(data, 'reason', 'operator_stop')}.`;
  }
  if (eventName === 'computer_use.recovery_loaded') {
    return data.resume_allowed === true
      ? 'Session was recovered and can continue safely.'
      : 'Session was recovered, but it cannot continue from the current state.';
  }
  if (eventName === 'computer_use.recovery_not_resumable') {
    return 'Recovery snapshot loaded, but the session is not resumable.';
  }
  if (eventName === 'computer_use.surface_mismatch') {
    return `Execution halted before action because the surface drifted: ${readString(data, 'reason_code', 'unknown')}.`;
  }
  if (eventName === 'computer_use.file_operation_mismatch') {
    return `File or dialog verification failed: ${readString(data, 'reason_code', 'unknown')}.`;
  }
  if (eventName === 'computer_use.file_operation_verified') {
    return `Verified ${readString(data, 'action_id', 'file operation')} against filesystem state.`;
  }
  if (eventName === 'session_paused') {
    const reason = readString(data, 'reason', 'operator_pause');
    return reason === 'approval_required'
      ? 'Session is waiting on approval.'
      : `Session paused: ${reason}.`;
  }
  if (eventName === 'session_resumed') {
    return `Session resumed after ${readString(data, 'reason', 'operator_resume')}.`;
  }
  if (eventName === 'session_stopped') {
    return `Session stopped: ${readString(data, 'reason', 'stop_requested')}.`;
  }
  if (eventName === 'session_completed') {
    return 'Computer-use session completed.';
  }
  if (eventName.includes('snapshot_drift')) {
    return 'Snapshot drift detected during resume verification.';
  }
  if (eventName.includes('approval_consumed')) {
    return 'Approval was consumed and execution may continue.';
  }
  if (eventName.includes('team_complete') || eventName.includes('task_completed')) {
    return 'Execution reached a terminal state.';
  }
  return humanizeEvent(eventName || 'event');
}

function detectRecoveryState(
  sessionState: JsonRecord,
): { state: WorkspaceRuntimeState['recoveryState']; summary: string | null; count: number } {
  const registry = asRecord(sessionState.registry);
  const recovery = asRecord(sessionState.recovery);
  if (Object.keys(recovery).length === 0) {
    return { state: null, summary: null, count: 0 };
  }
  const activeSession = Object.keys(registry).length > 0;
  const controlHistoryCount = asArray(recovery.control_history).length;
  if (activeSession) {
    return { state: null, summary: null, count: controlHistoryCount };
  }
  if (recovery.resume_allowed === true) {
    return {
      state: 'recovered',
      summary: 'Session was recovered from artifacts and can continue safely.',
      count: controlHistoryCount,
    };
  }
  return {
    state: 'non_resumable',
    summary: 'Session was recovered from artifacts, but it cannot continue from the current state.',
    count: controlHistoryCount,
  };
}

export function deriveWorkspaceRuntimeState(input: {
  runStatus: unknown;
  sessionState?: unknown;
  pendingApprovals: unknown[];
  linkedApprovals: unknown[];
}): WorkspaceRuntimeState {
  const runStatus = asRecord(input.runStatus);
  const job = asRecord(runStatus.job);
  const computerUse = asRecord(runStatus.computer_use);
  const worldModel = asRecord(computerUse.world_model);
  const sessionState = asRecord(input.sessionState);
  const registry = asRecord(sessionState.registry);
  const recovery = asRecord(sessionState.recovery);
  const linkedApprovals = input.linkedApprovals.map((item) => asRecord(item));
  const pendingApprovals = input.pendingApprovals.map((item) => asRecord(item));
  const approvals = linkedApprovals.length > 0 ? linkedApprovals : pendingApprovals;
  const pendingApproval = approvals.find((item) => readString(item, 'status').toLowerCase() === 'pending');
  const pendingApprovalId =
    readNullableString(computerUse, 'pending_approval_id') ||
    readNullableString(asRecord(pendingApproval ?? {}), 'approval_id');
  const rawState =
    readString(computerUse, 'session_state') ||
    readString(computerUse, 'lifecycle_state') ||
    readString(registry, 'state') ||
    readString(job, 'status', 'unknown');
  const rawStateLower = rawState.toLowerCase();
  const registryState = readNullableString(registry, 'state');
  const activeSession = Object.keys(registry).length > 0;
  const { state: recoveryState, summary: recoverySummary, count: controlHistoryCount } =
    detectRecoveryState(sessionState);
  const lastControlCommand = asRecord(computerUse.last_control_command);
  const pendingCommand =
    asRecord(computerUse.pending_command).command_type ??
    asRecord(recovery.pending_control_command).command_type ??
    null;
  const lastControlResult = asRecord(computerUse.last_control_result);
  const resumeAllowed =
    readBool(computerUse, 'resume_allowed') || readBool(recovery, 'resume_allowed');
  const stoppedByUser = readBool(computerUse, 'stopped_by_user');
  const lastVerification = asRecord(computerUse.last_verification_result);
  const worldModelVerification = asRecord(worldModel.last_verification_result);
  const lastVerificationSummary =
    readNullableString(lastVerification, 'summary') ||
    readNullableString(worldModelVerification, 'summary') ||
    readNullableString(worldModel, 'last_verified_effect') ||
    readNullableString(computerUse, 'last_verified_effect');

  let displayState: WorkspaceRuntimeStateKey;
  if (recoveryState === 'recovered') {
    displayState = 'recovered';
  } else if (recoveryState === 'non_resumable') {
    displayState = 'non_resumable';
  } else if (rawStateLower === 'awaiting_approval') {
    displayState = 'awaiting_approval';
  } else if (rawStateLower === 'paused' || rawStateLower === 'pausing') {
    displayState = 'paused';
  } else if (rawStateLower === 'resuming') {
    displayState = 'resuming';
  } else if (rawStateLower === 'stopping') {
    displayState = 'stopping';
  } else if (rawStateLower === 'stopped') {
    displayState = 'stopped';
  } else if (rawStateLower === 'completed') {
    displayState = 'completed';
  } else if (rawStateLower === 'failed') {
    displayState = 'failed';
  } else {
    displayState = 'running';
  }

  const canPause = activeSession && ['queued', 'starting', 'running', 'resuming'].includes(rawStateLower);
  const canResume = activeSession && rawStateLower === 'paused' && resumeAllowed;
  const canStop = activeSession && !['completed', 'failed', 'stopped'].includes(rawStateLower);

  return {
    displayState,
    rawState,
    registryState,
    activeSession,
    recoveryState,
    recoverySummary,
    controlHistoryCount,
    pendingApprovalId,
    pendingCommand: typeof pendingCommand === 'string' ? pendingCommand : null,
    lastSafeCheckpoint:
      readNullableString(computerUse, 'last_safe_checkpoint') ||
      readNullableString(worldModel, 'last_safe_checkpoint'),
    lastControlCommand:
      readNullableString(lastControlCommand, 'command_type') ||
      (typeof pendingCommand === 'string' ? pendingCommand : null),
    lastControlOutcome: readNullableString(lastControlResult, 'outcome'),
    lastControlReason:
      readNullableString(lastControlResult, 'reason') || readNullableString(lastControlCommand, 'reason'),
    resumeAllowed,
    stoppedByUser,
    lastVerificationSummary,
    canPause,
    canResume,
    canStop,
  };
}

function deriveStage(
  job: JsonRecord,
  computerUse: JsonRecord,
  runtimeState: WorkspaceRuntimeState,
  events: unknown[],
  approvals: JsonRecord[],
): { stage: WorkspaceStageKey; blockedReason: string | null } {
  const lifecycle = readString(computerUse, 'session_state', readString(computerUse, 'lifecycle_state')).toLowerCase();
  const runtimeStage = readString(computerUse, 'stage').toLowerCase();
  const runtimeError = readString(computerUse, 'last_error') || null;
  const status = readString(job, 'status').toLowerCase();
  const hasDrift = events.some((item) => {
    const eventName = readString(asRecord(item), 'event').toLowerCase();
    return eventName.includes('snapshot_drift') || eventName.includes('stale_approval');
  });
  if (hasDrift) {
    return { stage: 'blocked', blockedReason: 'snapshot_drift' };
  }

  if (runtimeState.displayState === 'stopped') {
    return {
      stage: 'blocked',
      blockedReason: runtimeState.stoppedByUser ? 'stopped_by_user' : runtimeError || 'session_stopped',
    };
  }

  if (['failed', 'non_resumable', 'recovered', 'paused', 'stopping'].includes(runtimeState.displayState)) {
    return {
      stage: 'blocked',
      blockedReason: runtimeState.lastControlReason || runtimeError || lifecycle || runtimeState.displayState,
    };
  }

  if (runtimeState.displayState === 'completed' || lifecycle === 'completed' || runtimeStage === 'completed') {
    return { stage: 'done', blockedReason: null };
  }

  if (runtimeState.displayState === 'awaiting_approval' || runtimeStage === 'require_approval') {
    return { stage: 'waiting_approval', blockedReason: runtimeError };
  }

  if (runtimeStage === 'verify') {
    return { stage: 'verifying', blockedReason: null };
  }

  if (['execute', 'decide_action', 'classify_risk', 'checkpoint', 'recover'].includes(runtimeStage)) {
    return { stage: 'executing', blockedReason: null };
  }

  if (['observe', 'interpret_state', 'compare_state'].includes(runtimeStage)) {
    return { stage: 'reading_screen', blockedReason: null };
  }

  if (runtimeStage === 'plan') {
    return { stage: 'planning', blockedReason: null };
  }

  const isDone =
    ['completed', 'succeeded', 'done', 'success'].includes(status) ||
    Boolean(readString(job, 'finished_at')) ||
    Boolean(readString(job, 'final_output'));
  if (isDone) {
    return { stage: 'done', blockedReason: null };
  }

  const hasPendingApproval = approvals.some(
    (item) => readString(item, 'status').toLowerCase() === 'pending',
  );
  if (status === 'blocked' || hasPendingApproval) {
    return { stage: 'waiting_approval', blockedReason: null };
  }

  const hasExecutionEvent = events.some((item) => {
    const eventName = readString(asRecord(item), 'event').toLowerCase();
    return eventName.includes('task_started') || eventName.includes('task_running');
  });
  if (status === 'running' && hasExecutionEvent) {
    return { stage: 'executing', blockedReason: null };
  }

  if (events.length > 0) {
    return { stage: 'reading_screen', blockedReason: null };
  }

  return { stage: 'planning', blockedReason: null };
}

function buildLiveSurface(runStatus: JsonRecord, approvals: JsonRecord[]): WorkspaceLiveSurface | null {
  const computerUse = asRecord(runStatus.computer_use);
  const worldModel = asRecord(computerUse.world_model);
  const activeWindow = asRecord(worldModel.active_window);
  const approval = approvals.find((item) => {
    const snapshot = asRecord(item.snapshot);
    return Object.keys(snapshot).length > 0;
  });
  if (Object.keys(worldModel).length > 0 || Object.keys(computerUse).length > 0) {
    const snapshot = asRecord(approval?.snapshot);
    const approvalRecord = asRecord(approval);
    const selectorContext = asRecord(snapshot.selector_context);
    const visibleTargetSet = asArray(worldModel.visible_target_set).map((item) => String(item));
    return {
      appIdentity:
        readString(worldModel, 'active_application_identity') ||
        readString(computerUse, 'active_app') ||
        readString(snapshot, 'app_identity', 'unknown'),
      windowIdentity:
        readString(activeWindow, 'window_identity') ||
        readString(computerUse, 'active_window') ||
        readString(snapshot, 'window_identity', 'unknown'),
      targetRef:
        readString(snapshot, 'target_ref') ||
        readString(worldModel, 'current_url') ||
        visibleTargetSet[0] ||
        'unknown',
      selector:
        visibleTargetSet[0] ||
        readString(selectorContext, 'selector') ||
        readString(snapshot, 'target_ref', 'n/a'),
      riskClass:
        readString(snapshot, 'risk_class') ||
        (readString(computerUse, 'pending_approval_id') ? 'guarded' : 'bounded'),
      expectedEffect:
        readString(worldModel, 'last_verified_effect') ||
        readString(computerUse, 'last_verified_effect') ||
        readString(asRecord(snapshot.action_plan), 'expected_effect', 'Awaiting next verified effect.'),
      approvalId:
        readString(computerUse, 'pending_approval_id') ||
        readString(approvalRecord, 'approval_id') ||
        null,
    };
  }
  if (!approval) {
    return null;
  }
  const snapshot = asRecord(approval.snapshot);
  const selectorContext = asRecord(snapshot.selector_context);
  const actionPlan = asRecord(snapshot.action_plan);
  return {
    appIdentity: readString(snapshot, 'app_identity', 'unknown'),
    windowIdentity: readString(snapshot, 'window_identity', 'unknown'),
    targetRef: readString(snapshot, 'target_ref', 'unknown'),
    selector: readString(selectorContext, 'selector', 'n/a'),
    riskClass: readString(snapshot, 'risk_class', 'unknown'),
    expectedEffect: readString(actionPlan, 'expected_effect', 'No expected effect declared.'),
    approvalId: readString(approval, 'approval_id') || null,
  };
}

function buildTranscript(
  objective: string,
  stage: WorkspaceStageKey,
  blockedReason: string | null,
  liveSurface: WorkspaceLiveSurface | null,
  runtimeState: WorkspaceRuntimeState,
  approvals: JsonRecord[],
  job: JsonRecord,
  computerUse: JsonRecord,
): WorkspaceTranscriptEntry[] {
  const entries: WorkspaceTranscriptEntry[] = [];
  if (objective) {
    entries.push({
      id: 'objective',
      role: 'user',
      title: 'Objective',
      body: objective,
    });
  }

  const stageBody = {
    planning: 'Preparing the run, loading context, and staging the first control loop.',
    reading_screen: 'Grounding the next step against the current surface before acting.',
    waiting_approval: 'Approval is required before the next external or device-facing action.',
    executing: 'Executing the next bounded step on the active surface with guardrails in place.',
    verifying: 'Checking observed state against the expected effect before continuing.',
    blocked: 'The run is paused because safety or drift checks prevented continuation.',
    done: 'The run reached a terminal state. Review artifacts and replay for follow-up.',
  }[stage];
  entries.push({
    id: 'stage',
    role: stage === 'blocked' ? 'system' : 'assistant',
    title: humanizeEvent(stage),
    body: stageBody,
    pending: stage !== 'done' && stage !== 'blocked',
  });

  if (liveSurface) {
    entries.push({
      id: 'surface',
      role: 'assistant',
      title: 'Live surface',
      body: `${liveSurface.appIdentity} · ${liveSurface.windowIdentity} · ${liveSurface.expectedEffect}`,
    });
  }

  entries.push({
    id: 'runtime-state',
    role: ['awaiting_approval', 'paused', 'stopping', 'stopped', 'recovered', 'non_resumable'].includes(
      runtimeState.displayState,
    )
      ? 'system'
      : 'assistant',
    title: 'Runtime state',
    body: `Session is ${humanizeValue(runtimeState.displayState)}. Raw state: ${humanizeValue(runtimeState.rawState)}.`,
    pending: ['running', 'resuming'].includes(runtimeState.displayState),
  });

  const currentUrl = readString(computerUse, 'current_url');
  if (currentUrl) {
    entries.push({
      id: 'url',
      role: 'assistant',
      title: 'Current URL',
      body: currentUrl,
    });
  }

  const pendingApproval = approvals.find(
    (item) => readString(item, 'status').toLowerCase() === 'pending',
  );
  if (pendingApproval) {
    entries.push({
      id: 'approval',
      role: 'system',
      title: 'Approval gate',
      body: `Pending approval ${readString(pendingApproval, 'approval_id')} keeps the run visible and interruptible.`,
    });
  }

  if (runtimeState.lastControlCommand) {
    entries.push({
      id: 'control',
      role: 'system',
      title: 'Control history',
      body: `Last control: ${humanizeValue(runtimeState.lastControlCommand)} (${humanizeValue(
        runtimeState.lastControlOutcome,
      )}${runtimeState.lastControlReason ? ` · ${humanizeValue(runtimeState.lastControlReason)}` : ''}).`,
    });
  }

  if (runtimeState.recoverySummary) {
    entries.push({
      id: 'recovery',
      role: 'system',
      title: 'Recovery',
      body: runtimeState.recoverySummary,
    });
  }

  if (runtimeState.lastVerificationSummary) {
    entries.push({
      id: 'verification',
      role: 'assistant',
      title: 'Last verification',
      body: runtimeState.lastVerificationSummary,
    });
  }

  const finalOutput = readString(job, 'final_output');
  if (finalOutput) {
    entries.push({
      id: 'final',
      role: 'assistant',
      title: 'Result',
      body: finalOutput,
    });
  }

  if (blockedReason) {
    entries.push({
      id: 'blocked',
      role: 'system',
      title: 'Blocked reason',
      body: humanizeEvent(blockedReason),
    });
  }

  return entries;
}

function shouldSuppressLegacyEvent(row: JsonRecord, events: unknown[]): boolean {
  const eventName = readString(row, 'event');
  const hasSpecific = (target: string) =>
    events.some((item) => readString(asRecord(item), 'event').toLowerCase() === target);
  if (eventName === 'session_resumed' && hasSpecific('computer_use.resumed')) {
    return true;
  }
  if (eventName === 'session_stopped' && hasSpecific('computer_use.stopped')) {
    return true;
  }
  if (eventName === 'session_paused') {
    const reason = readString(asRecord(row.data), 'reason', '');
    return reason !== 'approval_required' && hasSpecific('computer_use.paused');
  }
  return false;
}

function buildArtifacts(artifactsByName: Record<string, unknown>): WorkspaceArtifactEntry[] {
  return Object.entries(artifactsByName).map(([name, value]) => {
    const payload = asRecord(asRecord(value).payload);
    const computerUseArtifacts = asRecord(asRecord(payload.computer_use).artifacts);
    const available = hasMeaningfulPayload(payload);
    const summary =
      readString(payload, 'job_dir') ||
      (name === 'status.json' && Object.keys(computerUseArtifacts).length > 0
        ? `${Object.keys(computerUseArtifacts).length} runtime artifacts tracked`
        : '') ||
      readString(payload, 'audit_envelope_path') ||
      (available ? `${Object.keys(payload).length} fields available` : 'Not loaded');
    return { name, available, summary };
  });
}

export function buildWorkspaceSnapshot(input: {
  runStatus: unknown;
  sessionState?: unknown;
  events: unknown[];
  pendingApprovals: unknown[];
  linkedApprovals: unknown[];
  artifactsByName: Record<string, unknown>;
}): WorkspaceSnapshot {
  const runStatus = asRecord(input.runStatus);
  const job = asRecord(runStatus.job);
  const computerUse = asRecord(runStatus.computer_use);
  const objective = readString(job, 'request');
  const approvalsSource = input.linkedApprovals.length > 0 ? input.linkedApprovals : input.pendingApprovals;
  const approvals = approvalsSource.map((item) => asRecord(item));
  const runtimeState = deriveWorkspaceRuntimeState({
    runStatus,
    sessionState: input.sessionState,
    pendingApprovals: input.pendingApprovals,
    linkedApprovals: input.linkedApprovals,
  });
  const { stage, blockedReason } = deriveStage(job, computerUse, runtimeState, input.events, approvals);
  const liveSurface = buildLiveSurface(runStatus, approvals);
  const timeline = input.events
    .map((item) => asRecord(item))
    .filter((row) => !shouldSuppressLegacyEvent(row, input.events))
    .map((row, index) => {
      const eventName = readString(row, 'event', 'event');
      const lowerName = eventName.toLowerCase();
      const tone: WorkspaceTimelineEntry['tone'] =
        lowerName.includes('failed') ||
        lowerName.includes('stopped') ||
        lowerName.includes('drift') ||
        lowerName.includes('rejected') ||
        lowerName.includes('mismatch') ||
        lowerName.includes('approval_required')
          ? 'warning'
          : lowerName.includes('verified') ||
              lowerName.includes('completed') ||
              lowerName.includes('resumed') ||
              lowerName.includes('consumed') ||
              lowerName.includes('recovery_loaded')
            ? 'success'
            : lowerName.includes('approval') || lowerName.includes('paused')
              ? 'warning'
              : 'neutral';
      return {
        id: `${index}-${readString(row, 'event_id', eventName)}`,
        event: eventName,
        timestamp: readString(row, 'timestamp'),
        phase: readString(row, 'phase'),
        summary: summarizeEvent(row),
        tone,
      };
    });
  const transcript = buildTranscript(
    objective,
    stage,
    blockedReason,
    liveSurface,
    runtimeState,
    approvals,
    job,
    computerUse,
  );
  return {
    objective,
    stage,
    progressIndex: Math.max(0, PROGRESS_STAGES.indexOf(stage === 'blocked' ? 'waiting_approval' : stage)),
    progressTotal: PROGRESS_STAGES.length,
    currentStatus: runtimeState.rawState || readString(job, 'status', 'unknown'),
    blockedReason,
    liveSurface,
    runtimeState,
    transcript,
    timeline,
    artifacts: buildArtifacts(input.artifactsByName),
  };
}

export function listAttachmentLabels(runId: string, specPath: string, rootDir: string): string[] {
  const labels: string[] = [];
  if (specPath.trim()) {
    labels.push(`Spec: ${specPath.trim()}`);
  }
  if (runId.trim()) {
    labels.push(`Run: ${runId.trim()}`);
  }
  if (rootDir.trim()) {
    labels.push(`Root: ${rootDir.trim()}`);
  }
  return labels;
}

export function readWorkspaceProgress(snapshot: WorkspaceSnapshot): number {
  return ((snapshot.progressIndex + 1) / snapshot.progressTotal) * 100;
}

export function countTimelineByTone(
  timeline: WorkspaceTimelineEntry[],
  tone: WorkspaceTimelineEntry['tone'],
): number {
  return timeline.filter((item) => item.tone === tone).length;
}

export function selectRecentRuns(runs: unknown[], limit = 4): JsonRecord[] {
  return asArray(runs)
    .map((item) => asRecord(item))
    .filter((item) => Object.keys(item).length > 0)
    .slice(0, limit);
}
