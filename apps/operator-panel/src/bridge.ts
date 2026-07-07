import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

import { previewAssistantProviderModels, previewAssistantStartTurn } from './assistant/assistantFixtures';
import {
  normalizeAssistantKnowledgeSearchResponse,
  previewAssistantKnowledgeSearch,
  type AssistantKnowledgeSearchResponse,
} from './assistant/assistantSystemKnowledge';
import {
  normalizeAssistantTaskPlan,
  normalizeAssistantTaskSubmissionResult,
} from './assistant/assistantTaskingMappers';
import type {
  AssistantTaskPlan,
  AssistantTaskSubmissionResult,
} from './assistant/assistantTaskingTypes';
import type {
  AssistantCancelTurnResponse,
  AssistantStartTurnOptions,
  AssistantStartTurnResponse,
  AssistantStreamEvent,
} from './assistant/assistantTypes';
import type {
  AssistantProviderModelsRequest,
  AssistantProviderModelsResponse,
} from './assistant/modelDiscovery';
import {
  previewApprovalDetail,
  previewApprovalPending,
  previewArtifact,
  previewBackupCreate,
  previewBackupVerify,
  previewComputerUseControl,
  previewControlPlaneAgentList,
  previewControlPlaneClaims,
  previewControlPlaneDoctor,
  previewControlPlanePolicySimulation,
  previewControlPlaneSnapshot,
  previewComputerUseSummary,
  previewComputerUseSessionState,
  previewComputerUseSubmitResponse,
  previewConfigResolve,
  previewGaReadiness,
  previewHandshake,
  previewIdentity,
  previewInstallRehearsal,
  previewKeysStatus,
  previewMigrateApplyDryRun,
  previewMigratePlan,
  previewMetricsSnapshot,
  previewPermissionCheck,
  previewQualification,
  previewRestoreVerify,
  previewRunDetail,
  previewRunReplay,
  previewRunSummary,
  previewSecurityBaseline,
  previewSecurityReview,
  previewSubmitResponse,
  previewSupportBundle,
  previewTailEvents,
} from './previewFixtures';
import type { PanelSettings } from './settings';
import type { ComputerUseRuntimeChoice } from './capabilities';
import type { ControlPlaneSnapshot } from './control-plane/types';

export type BridgeErrorCode =
  | 'INVALID_INPUT'
  | 'PATH_VIOLATION'
  | 'TIMEOUT'
  | 'CLI_NOT_FOUND'
  | 'CLI_FAILED'
  | 'PARSE_FAILED'
  | 'SCHEMA_FAILED'
  | 'CANCELLED';

export interface BridgeErrorPayload {
  code: BridgeErrorCode;
  message: string;
  stderrPreview: string;
  command: string;
  retryable: boolean;
}

export type BridgeResult<T> =
  | {
      ok: true;
      data: T;
      error: null;
    }
  | {
      ok: false;
      data: null;
      error: BridgeErrorPayload;
    };

export interface BridgeConfig {
  mode: 'auto' | 'external' | 'bundled';
  cliPath?: string;
  bundledPythonPath?: string;
  profile: string;
  rootDir: string;
  env?: Record<string, string>;
  timeoutMs?: number;
}

export interface TailEventsResponse {
  contractVersion: string;
  events: unknown[];
  nextCursor: number;
  reset: boolean;
  truncated: boolean;
  badLineCount: number;
}

export interface SubmitTeamRunOptions {
  specPath: string;
  request: string;
  caseId?: string;
  jobId?: string;
  provider?: string;
  fallbackProvider?: string;
  model?: string;
  hfModelId?: string;
  safetyOptions?: TaskSafetyOptions;
}

export interface SubmitComputerUseRunOptions {
  request: string;
  caseId?: string;
  jobId?: string;
  mode?: 'dry_run' | 'step_approval' | 'execute';
  runtime?: ComputerUseRuntimeChoice;
  provider?: string;
  fallbackProvider?: string;
  model?: string;
  hfModelId?: string;
  safetyOptions?: TaskSafetyOptions;
}

export interface TaskSafetyOptions {
  askBeforeExternalAction: boolean;
  askBeforeDelete: boolean;
  askBeforeSend: boolean;
}

export interface ResumeTeamRunOptions {
  specPath: string;
  sourceJobId: string;
  resumeJobId?: string;
  provider?: string;
  fallbackProvider?: string;
  model?: string;
  hfModelId?: string;
}

export interface ConfigResolveOptions {
  provider?: string;
  fallbackProvider?: string;
  model?: string;
  hfModelId?: string;
}

export interface QualificationRunOptions extends ConfigResolveOptions {
  mode?: string;
  soakHours?: number;
  outputRoot?: string;
  workloads?: string;
  mergeFromReport?: string;
}

export interface GaReadinessOptions {
  report?: string;
  qualificationReport?: string;
}

export interface InstallRehearsalOptions {
  targetRoot?: string;
  output?: string;
  mode?: 'source-cli' | 'operator-panel-smoke';
}

export interface SecurityReviewOptions {
  outputRoot?: string;
  evidenceRoot?: string;
}

export interface KeyRotatePlanOptions {
  nextKeyId?: string;
  activateAt?: string;
  retireAfter?: string;
}

export interface ControlPlaneRunSubmitOptions {
  agentId: string;
  prompt: string;
  operatorId: string;
}

export interface AssistantTaskPlanOptions {
  message: string;
  operatorId?: string;
  workspaceId?: string;
  agentHint?: string;
}

export interface AssistantTaskSubmitOptions {
  proposalId: string;
  confirmPlanHash: string;
  operatorId: string;
}

export interface LocalProductReadinessOptions {
  target?: string;
}

export interface ControlPlaneEvidenceExportOptions {
  runId: string;
  outputDir?: string;
}

export type AssistantEventUnlisten = () => void;

export class BridgeError extends Error {
  readonly payload: BridgeErrorPayload;

  constructor(payload: BridgeErrorPayload) {
    super(payload.message);
    this.name = 'BridgeError';
    this.payload = payload;
  }
}

function toBridgeConfig(settings: PanelSettings, timeoutMs = 15000): BridgeConfig {
  const openAiApiKey = settings.assistantOpenAiApiKey.trim();
  const deepSeekApiKey = settings.assistantDeepSeekApiKey.trim();
  const remoteProvidersEnabled = Boolean(openAiApiKey || deepSeekApiKey);

  return {
    mode: settings.mode,
    cliPath: settings.cliPath.trim() || undefined,
    bundledPythonPath: settings.bundledPythonPath.trim() || undefined,
    profile: settings.profile,
    rootDir: settings.rootDir,
    env: {
      BINLIQUID_PROFILE_NAME: settings.profile,
      BINLIQUID_TEAM_ARTIFACT_DIR: settings.rootDir,
      ...(remoteProvidersEnabled ? { BINLIQUID_REMOTE_PROVIDERS_ENABLED: 'true' } : {}),
      ...(openAiApiKey ? { OPENAI_API_KEY: openAiApiKey } : {}),
      ...(deepSeekApiKey ? { DEEPSEEK_API_KEY: deepSeekApiKey } : {}),
    },
    timeoutMs,
  };
}

function isTauriRuntime(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

type PreviewEnvironment = {
  DEV?: boolean;
  MODE?: string;
  VITE_OPERATOR_PANEL_PREVIEW?: string | boolean;
};

export function isPreviewAllowedForEnv(env: PreviewEnvironment): boolean {
  return (
    env.DEV === true ||
    env.MODE === 'test' ||
    env.VITE_OPERATOR_PANEL_PREVIEW === '1' ||
    env.VITE_OPERATOR_PANEL_PREVIEW === 'true' ||
    env.VITE_OPERATOR_PANEL_PREVIEW === true
  );
}

function isPreviewAllowed(): boolean {
  return isPreviewAllowedForEnv(import.meta.env);
}

export function isBridgePreviewMode(): boolean {
  return !isTauriRuntime() && isPreviewAllowed();
}

async function callBridge<T>(command: string, args: Record<string, unknown>): Promise<T> {
  if (!isTauriRuntime()) {
    throw new BridgeError({
      code: 'CLI_NOT_FOUND',
      message:
        'Operator Panel bridge is unavailable. Run inside Tauri or enable VITE_OPERATOR_PANEL_PREVIEW=1 for explicit browser preview.',
      stderrPreview: '',
      command,
      retryable: false,
    });
  }

  const result = await invoke<BridgeResult<T>>(command, args);
  if (!result.ok) {
    throw new BridgeError(result.error);
  }
  return result.data;
}


function withTimeout(settings: PanelSettings, timeoutMs: number): BridgeConfig {
  return toBridgeConfig(settings, timeoutMs);
}

function previewAssistantTaskPlan(message: string): AssistantTaskPlan {
  return normalizeAssistantTaskPlan({
    schemaVersion: 'assistant-tasking.plan/v1',
    proposalId: 'astp_preview_write_fixture',
    planHash: 'sha256:99719f8157f65dbb65e653d28c371889ed9e81cbb843b6f24700d31e2b023944',
    status: 'planned',
    intentKind: 'plan_agent_task',
    selectedAgent: {
      agentId: 'external-agent',
      label: 'external-agent',
      enrolled: true,
      workspaceId: 'pilot-workspace',
      principalId: 'principal-agent',
      allowedSurfaces: ['external_gateway'],
      blockedSurfaces: [],
      declaredActions: ['read', 'external_write'],
      qualificationStatus: 'ready',
      blockingReasons: [],
    },
    candidateAgents: [
      {
        agentId: 'external-agent',
        label: 'external-agent',
        enrolled: true,
        workspaceId: 'pilot-workspace',
        principalId: 'principal-agent',
        allowedSurfaces: ['external_gateway'],
        blockedSurfaces: [],
        declaredActions: ['read', 'external_write'],
        qualificationStatus: 'ready',
        blockingReasons: [],
      },
    ],
    taskSummary: message || 'Preview governed assistant task',
    riskClass: 'external_write',
    policyPreview: {
      decision: 'require_approval',
      riskClass: 'external_write',
      approvalRequired: true,
      safeToSubmit: true,
      reasonCode: 'ASSISTANT_TASK_WRITE_REQUIRES_APPROVAL',
      blockedReasons: [],
    },
    approvalRequired: true,
    submitMode: 'proposal_first',
    idempotencyKey: 'assistant-task:astp_preview_write_fixture',
    evidenceExpectation: {
      mode: 'hash_only_redacted',
      expectedRefs: ['artifacts/assistant-tasking/proposals/astp_preview_write_fixture.json'],
      rawContentPersisted: false,
    },
    safeToSubmit: true,
    blockedReasons: [],
    sourceRefs: ['docs/ASSISTANT_GOVERNED_TASKING.md'],
    createdAtUtc: '2026-01-01T00:00:00Z',
  });
}

function previewAssistantTaskSubmission(options: AssistantTaskSubmitOptions): AssistantTaskSubmissionResult {
  return normalizeAssistantTaskSubmissionResult({
    schemaVersion: 'assistant-tasking.submission/v1',
    proposalId: options.proposalId,
    planHash: options.confirmPlanHash,
    status: 'blocked_pending_approval',
    policyDecision: 'require_approval',
    reasonCode: 'ASSISTANT_TASK_WRITE_REQUIRES_APPROVAL',
    runId: 'agt-preview-001',
    approvalId: 'apr-preview-task-001',
    evidenceRef: 'artifacts/assistant-tasking/submissions/agt-preview-001.json',
    replayStatus: 'not_replayed',
    idempotencyStatus: 'created',
    blockedReasons: [],
    nextActions: ['approval.show', 'approval.decide', 'approval.execute'],
    generatedAtUtc: '2026-01-01T00:00:01Z',
  });
}

function previewLocalProductReadiness(target = 'windows-x64'): unknown {
  return {
    schemaVersion: 'local_product_readiness/v1',
    profile: 'enterprise',
    overallStatus: 'pass',
    target: {
      os: 'windows',
      arch: 'x64',
      targetId: target,
      supportTier: 'supported',
      claimAllowed: true,
      reasonCodes: [],
    },
    claimBoundary: {
      schemaVersion: 'local_product_claim_boundary/v1',
      targetId: target,
      claimAllowed: true,
      supportedClaims: [target],
      notEvidencedTargets: ['darwin-arm64', 'darwin-x64', 'linux-x64'],
      unsupportedTargets: [],
      blockedTargets: [],
      productClaimSummary: `Claims are limited to evidenced target ${target}.`,
      blockingReasons: [],
    },
    rawPromptPersisted: false,
    liveComputerUseEnabled: false,
  };
}

function previewLocalProductMatrix(): unknown {
  return {
    schemaVersion: 'local_product_readiness_matrix/v1',
    targets: [previewLocalProductReadiness('windows-x64')],
    supportedClaims: ['windows-x64'],
    notEvidencedTargets: ['darwin-arm64', 'darwin-x64', 'linux-x64'],
    unsupportedTargets: [],
    blockedTargets: [],
    productClaimSummary: 'Supported platform claims are limited to evidenced targets: windows-x64',
  };
}

function previewPlatformEvidenceStatus(): unknown {
  return {
    artifactVersion: 'local-product-platform-reconciliation/v1',
    status: 'pass',
    gitCommit: 'preview',
    claimedTargets: [],
    evidencedTargets: ['windows-x64'],
    notEvidencedTargets: ['darwin-arm64', 'darwin-x64', 'linux-x64'],
    noShipBlockers: [],
    warnings: [],
    targets: {
      'windows-x64': { targetId: 'windows-x64', status: 'evidenced', reasonCodes: [] },
      'darwin-arm64': {
        targetId: 'darwin-arm64',
        status: 'not_evidenced',
        reasonCodes: ['TARGET_NOT_EVIDENCED'],
      },
      'darwin-x64': {
        targetId: 'darwin-x64',
        status: 'not_evidenced',
        reasonCodes: ['TARGET_NOT_EVIDENCED'],
      },
      'linux-x64': {
        targetId: 'linux-x64',
        status: 'not_evidenced',
        reasonCodes: ['TARGET_NOT_EVIDENCED'],
      },
    },
  };
}

function previewRcHandoffStatus(): unknown {
  return {
    artifactVersion: 'local-product-rc-handoff/v1',
    status: 'ready',
    gitCommit: 'preview',
    branch: 'preview',
    reconciliationPath: 'platform_evidence_reconciliation.json',
    productClosurePath: 'artifacts/product-complete-closure/product_complete_closure_report.json',
    evidenceBundles: [],
    supportedClaims: ['windows-x64 source/local install evidenced'],
    blockedClaims: [],
    operatorNextSteps: ['Collect and import evidence for not-evidenced targets before claiming support.'],
  };
}

export async function handshake(settings: PanelSettings): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewHandshake(settings);
  }
  return callBridge('bridge_handshake', { config: toBridgeConfig(settings) });
}

export async function fetchControlPlaneDoctor(settings: PanelSettings): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewControlPlaneDoctor(settings);
  }
  return callBridge('bridge_control_plane_doctor', { config: toBridgeConfig(settings) });
}

export async function fetchControlPlaneSnapshot(settings: PanelSettings): Promise<ControlPlaneSnapshot> {
  if (isBridgePreviewMode()) {
    return previewControlPlaneSnapshot(settings) as ControlPlaneSnapshot;
  }
  return callBridge('bridge_control_plane_snapshot', { config: toBridgeConfig(settings, 30000) });
}

export async function listControlPlaneAgents(settings: PanelSettings): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewControlPlaneAgentList();
  }
  return callBridge('bridge_control_plane_agent_list', { config: toBridgeConfig(settings) });
}

export async function simulateControlPlanePolicy(
  settings: PanelSettings,
  agentId: string,
): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewControlPlanePolicySimulation();
  }
  return callBridge('bridge_control_plane_policy_simulate', {
    config: toBridgeConfig(settings),
    agentId,
  });
}

export async function submitControlPlaneRun(
  settings: PanelSettings,
  options: ControlPlaneRunSubmitOptions,
): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return {
      version: 'control-plane.run/v1',
      run_id: 'cp-run-preview-001',
      agent_id: options.agentId,
      profile: settings.profile,
      status: 'approval_pending',
      submitted_by: `ui:${options.operatorId}`,
      identity_ref: 'identity:preview',
      input_hash: 'sha256:preview',
      policy_hash: 'sha256:preview',
      started_at: '2026-05-31T00:00:00Z',
      completed_at: null,
      approval_ids: ['apr-preview-control-plane'],
      artifact_refs: [],
      evidence_pack_id: null,
      blocking_reasons: [],
      next_actions: ['approval.show', 'approval.decide', 'approval.execute'],
    };
  }
  return callBridge('bridge_control_plane_run_submit', {
    config: toBridgeConfig(settings, 30000),
    payload: {
      agentId: options.agentId,
      prompt: options.prompt,
      operatorId: options.operatorId,
    },
  });
}

export async function exportControlPlaneEvidence(
  settings: PanelSettings,
  options: ControlPlaneEvidenceExportOptions,
): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return {
      version: 'control-plane.evidence-pack/v1',
      pack_id: `evp-${options.runId}`,
      run_id: options.runId,
      agent_id: 'governed-ops',
      profile: settings.profile,
      runtime_version: '0.4.1',
      git_commit: 'preview',
      generated_at: '2026-05-31T00:00:00Z',
      items: [],
      redaction_summary: {
        raw_screenshots_persisted: 0,
        secrets_redacted: true,
        pii_redaction_enabled: true,
      },
      verification: {
        hash_chain_verified: true,
        signature_verified: true,
        replay_verified: true,
      },
      signature: {
        mode: 'ed25519_local_file',
        key_id: 'enterprise-signing-current',
        algorithm: 'ed25519',
        signature_ref: 'manifest.integrity.signature',
      },
      warnings: [],
    };
  }
  return callBridge('bridge_control_plane_evidence_export', {
    config: toBridgeConfig(settings, 60000),
    payload: { runId: options.runId, outputDir: options.outputDir },
  });
}

export async function verifyControlPlaneEvidence(
  settings: PanelSettings,
  manifestPath: string,
): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return {
      status: 'pass',
      hash_chain_verified: true,
      signature_verified: true,
      required_items_present: true,
      replay_verified: true,
      blocking_reasons: [],
      warnings: [],
    };
  }
  return callBridge('bridge_control_plane_evidence_verify', {
    config: toBridgeConfig(settings, 30000),
    manifestPath,
  });
}

export async function verifyControlPlaneClaims(settings: PanelSettings): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewControlPlaneClaims();
  }
  return callBridge('bridge_control_plane_claims_verify', { config: toBridgeConfig(settings) });
}

export async function fetchApprovals(settings: PanelSettings): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewApprovalPending();
  }
  return callBridge('bridge_approval_pending', { config: toBridgeConfig(settings) });
}

export async function showApproval(settings: PanelSettings, approvalId: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewApprovalDetail(approvalId);
  }
  return callBridge('bridge_approval_show', {
    config: toBridgeConfig(settings),
    approvalId,
  });
}

export async function decideApproval(
  settings: PanelSettings,
  approvalId: string,
  approve: boolean,
  operatorId: string,
  reason?: string,
): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return {
      contract_version: '2.0',
      approval_id: approvalId,
      error_code: null,
      ticket: {
        ...previewApprovalDetail(approvalId).ticket,
        status: approve ? 'approved' : 'rejected',
        actor: operatorId,
        decision_reason: reason ?? 'operator workspace action',
        decided_at: '2026-03-08T09:40:00Z',
      },
    };
  }
  return callBridge('bridge_approval_decide', {
    config: toBridgeConfig(settings),
    approvalId,
    approve,
    reason,
    operatorId,
  });
}

export async function executeApproval(
  settings: PanelSettings,
  approvalId: string,
  operatorId: string,
): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return {
      contract_version: '2.0',
      approval_id: approvalId,
      actor: operatorId,
      execution_used_path: 'llm_only',
      trace_id: 'trace-preview-execute',
      fallback_events: [],
      metrics: {
        router_reason_code: 'RULE_ROUTE',
      },
      ticket: {
        ...previewApprovalDetail(approvalId).ticket,
        status: 'executed',
        execution_status: 'executed',
        actor: operatorId,
        executed_at: '2026-03-08T09:41:00Z',
      },
    };
  }
  return callBridge('bridge_approval_execute', {
    config: toBridgeConfig(settings),
    approvalId,
    operatorId,
  });
}

export async function submitTeamRun(settings: PanelSettings, options: SubmitTeamRunOptions): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewSubmitResponse(settings, options.jobId);
  }
  return callBridge('bridge_team_submit', {
    config: toBridgeConfig(settings),
    specPath: options.specPath,
    request: options.request,
    caseId: options.caseId,
    jobId: options.jobId,
    provider: options.provider,
    fallbackProvider: options.fallbackProvider,
    model: options.model,
    hfModelId: options.hfModelId,
    safetyOptions: options.safetyOptions,
  });
}

export async function submitComputerUseRun(
  settings: PanelSettings,
  options: SubmitComputerUseRunOptions,
): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewComputerUseSubmitResponse(settings, options.jobId, options.runtime);
  }
  return callBridge('bridge_computer_use_submit', {
    config: toBridgeConfig(settings),
    request: options.request,
    caseId: options.caseId,
    jobId: options.jobId,
    mode: options.mode,
    runtime: options.runtime,
    provider: options.provider,
    fallbackProvider: options.fallbackProvider,
    model: options.model,
    hfModelId: options.hfModelId,
    safetyOptions: options.safetyOptions,
  });
}

export async function getComputerUseSummary(settings: PanelSettings, limit = 20): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewComputerUseSummary(settings, limit);
  }
  return callBridge('bridge_computer_use_summary', {
    config: toBridgeConfig(settings),
    limit,
  });
}

export async function pauseComputerUseSession(settings: PanelSettings, jobId: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewComputerUseControl(jobId, 'pause');
  }
  return callBridge('bridge_computer_use_pause', {
    config: toBridgeConfig(settings),
    jobId,
  });
}

export async function resumeComputerUseSession(settings: PanelSettings, jobId: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewComputerUseControl(jobId, 'resume');
  }
  return callBridge('bridge_computer_use_resume', {
    config: toBridgeConfig(settings),
    jobId,
  });
}

export async function stopComputerUseSession(settings: PanelSettings, jobId: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewComputerUseControl(jobId, 'stop');
  }
  return callBridge('bridge_computer_use_stop', {
    config: toBridgeConfig(settings),
    jobId,
  });
}

export async function getComputerUseSessionState(
  settings: PanelSettings,
  jobId: string,
): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewComputerUseSessionState(settings, jobId);
  }
  return callBridge('bridge_computer_use_state', {
    config: toBridgeConfig(settings),
    jobId,
  });
}

export async function resumeTeamRun(settings: PanelSettings, options: ResumeTeamRunOptions): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewSubmitResponse(settings, options.resumeJobId ?? `${options.sourceJobId}-resume-ui`);
  }
  return callBridge('bridge_team_resume_submit', {
    config: toBridgeConfig(settings),
    specPath: options.specPath,
    sourceJobId: options.sourceJobId,
    resumeJobId: options.resumeJobId,
    provider: options.provider,
    fallbackProvider: options.fallbackProvider,
    model: options.model,
    hfModelId: options.hfModelId,
  });
}

export async function listRuns(settings: PanelSettings, since?: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    const payload = previewRunSummary(settings) as Record<string, unknown>;
    if (since) {
      payload.since = since;
    }
    return payload;
  }
  return callBridge('bridge_team_list', {
    config: toBridgeConfig(settings),
    since,
  });
}

export async function getRunStatus(settings: PanelSettings, jobId: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewRunDetail(settings, jobId);
  }
  return callBridge('bridge_team_status', {
    config: toBridgeConfig(settings),
    jobId,
  });
}

export async function getRunReplay(settings: PanelSettings, jobId: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewRunReplay(jobId);
  }
  return callBridge('bridge_team_replay', {
    config: toBridgeConfig(settings),
    jobId,
  });
}

export async function exportRunArtifacts(
  settings: PanelSettings,
  jobId: string,
  exportDir: string,
): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return {
      contract_version: '2.0',
      status: 'ok',
      job_id: jobId,
      export_dir: exportDir,
      files: [
        `${exportDir}/status.json`,
        `${exportDir}/tasks.json`,
        `${exportDir}/handoffs.json`,
        `${exportDir}/audit_envelope.json`,
      ],
    };
  }
  return callBridge('bridge_team_export', {
    config: toBridgeConfig(settings),
    jobId,
    exportDir,
  });
}

export async function resolveConfig(settings: PanelSettings, options?: ConfigResolveOptions): Promise<unknown> {
  if (isBridgePreviewMode()) {
    const payload = previewConfigResolve(settings) as Record<string, unknown>;
    const resolved = (payload.resolved as Record<string, unknown>) ?? {};
    const sourceMap = (payload.source_map as Record<string, unknown>) ?? {};
    if (options?.provider) {
      resolved.llm_provider = options.provider;
      sourceMap.llm_provider = 'cli';
    }
    if (options?.fallbackProvider) {
      resolved.fallback_provider = options.fallbackProvider;
      sourceMap.fallback_provider = 'cli';
    }
    if (options?.model) {
      resolved.model_name = options.model;
      sourceMap.model_name = 'cli';
    }
    if (options?.hfModelId) {
      resolved.hf_model_id = options.hfModelId;
      sourceMap.hf_model_id = 'cli';
    }
    return payload;
  }
  return callBridge('bridge_config_resolve', {
    config: toBridgeConfig(settings),
    provider: options?.provider,
    fallbackProvider: options?.fallbackProvider,
    model: options?.model,
    hfModelId: options?.hfModelId,
  });
}

export async function fetchIdentity(settings: PanelSettings): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewIdentity(settings);
  }
  return callBridge('bridge_auth_whoami', {
    config: toBridgeConfig(settings),
  });
}

export async function checkPermission(settings: PanelSettings, permission: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewPermissionCheck(permission);
  }
  return callBridge('bridge_auth_check', {
    config: toBridgeConfig(settings),
    permission,
  });
}

export async function fetchSecurityBaseline(settings: PanelSettings): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewSecurityBaseline();
  }
  return callBridge('bridge_security_baseline', {
    config: withTimeout(settings, 30000),
  });
}

export async function runInstallRehearsal(settings: PanelSettings, options: InstallRehearsalOptions = {}): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewInstallRehearsal(options.targetRoot, options.output);
  }
  return callBridge('bridge_install_rehearsal', {
    config: withTimeout(settings, 120000),
    targetRoot: options.targetRoot,
    output: options.output,
    mode: options.mode,
  });
}

export async function generateSecurityReview(settings: PanelSettings, options: SecurityReviewOptions = {}): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewSecurityReview(options.outputRoot, options.evidenceRoot);
  }
  return callBridge('bridge_security_review', {
    config: withTimeout(settings, 120000),
    outputRoot: options.outputRoot,
    evidenceRoot: options.evidenceRoot,
  });
}

export async function fetchKeysStatus(settings: PanelSettings): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewKeysStatus();
  }
  return callBridge('bridge_keys_status', {
    config: toBridgeConfig(settings),
  });
}

export async function verifySignedArtifact(settings: PanelSettings, path: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return {
      contract_version: '2.0',
      path,
      verified: true,
      signature_verified: true,
      signature_mode: 'unsigned',
      key_id: 'enterprise-signing-current',
      error_code: null,
    };
  }
  return callBridge('bridge_keys_verify', {
    config: toBridgeConfig(settings),
    path,
  });
}

export async function rotateKeyPlan(settings: PanelSettings, options: KeyRotatePlanOptions): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return {
      contract_version: '2.0',
      provider: 'local_file',
      current_key_id: 'enterprise-signing-current',
      next_key_id: options.nextKeyId ?? 'next-signing-key',
      steps: ['prepare', 'dual-verify', 'activate', 'retire-old'],
      activate_at: options.activateAt ?? '2026-03-15T09:00:00Z',
      retire_after: options.retireAfter ?? '2026-03-29T09:00:00Z',
      enterprise_ready: true,
    };
  }
  return callBridge('bridge_keys_rotate_plan', {
    config: toBridgeConfig(settings),
    nextKeyId: options.nextKeyId,
    activateAt: options.activateAt,
    retireAfter: options.retireAfter,
  });
}

export async function exportSupportBundle(settings: PanelSettings, output?: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewSupportBundle(output);
  }
  return callBridge('bridge_support_bundle_export', {
    config: withTimeout(settings, 60000),
    output,
  });
}

export async function createBackup(settings: PanelSettings, outputDir?: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewBackupCreate(outputDir);
  }
  return callBridge('bridge_backup_create', {
    config: withTimeout(settings, 60000),
    outputDir,
  });
}

export async function verifyBackup(settings: PanelSettings, backupDir: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewBackupVerify(backupDir);
  }
  return callBridge('bridge_backup_verify', {
    config: withTimeout(settings, 30000),
    backupDir,
  });
}

export async function verifyRestore(settings: PanelSettings, backupDir: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewRestoreVerify(backupDir);
  }
  return callBridge('bridge_restore_verify', {
    config: withTimeout(settings, 30000),
    backupDir,
  });
}

export async function planMigration(settings: PanelSettings): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewMigratePlan();
  }
  return callBridge('bridge_migrate_plan', {
    config: toBridgeConfig(settings),
  });
}

export async function dryRunMigration(settings: PanelSettings): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewMigrateApplyDryRun();
  }
  return callBridge('bridge_migrate_apply_dry_run', {
    config: withTimeout(settings, 30000),
  });
}

export async function snapshotMetrics(settings: PanelSettings): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewMetricsSnapshot();
  }
  return callBridge('bridge_metrics_snapshot', {
    config: withTimeout(settings, 30000),
  });
}

export async function fetchGaReadiness(settings: PanelSettings, options?: GaReadinessOptions): Promise<unknown> {
  if (isBridgePreviewMode()) {
    const payload = previewGaReadiness() as Record<string, unknown>;
    if (options?.report) {
      payload.report = options.report;
    }
    if (options?.qualificationReport) {
      payload.qualification_report_path = options.qualificationReport;
    }
    return payload;
  }
  return callBridge('bridge_ga_readiness', {
    config: withTimeout(settings, 30000),
    report: options?.report,
    qualificationReport: options?.qualificationReport,
  });
}

export async function runQualification(settings: PanelSettings, options: QualificationRunOptions): Promise<unknown> {
  if (isBridgePreviewMode()) {
    const payload = previewQualification() as Record<string, unknown>;
    payload.mode = options.mode ?? 'mixed';
    payload.output_root = options.outputRoot ?? 'artifacts/qualification';
    return payload;
  }
  return callBridge('bridge_qualification_run', {
    config: withTimeout(settings, 120000),
    mode: options.mode,
    soakHours: options.soakHours,
    outputRoot: options.outputRoot,
    workloads: options.workloads,
    mergeFromReport: options.mergeFromReport,
    provider: options.provider,
    fallbackProvider: options.fallbackProvider,
    model: options.model,
    hfModelId: options.hfModelId,
  });
}

export async function readArtifact(
  settings: PanelSettings,
  jobId: string,
  artifactName: string,
  maxBytes = 256 * 1024,
): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewArtifact(settings, jobId, artifactName);
  }
  return callBridge('bridge_read_artifact', {
    rootDir: settings.rootDir,
    jobId,
    artifactName,
    maxBytes,
  });
}

export async function tailEvents(
  settings: PanelSettings,
  jobId: string,
  cursor: number,
  maxBytes = 128 * 1024,
  maxLines = 200,
): Promise<TailEventsResponse> {
  if (isBridgePreviewMode()) {
    const payload = previewTailEvents();
    if (cursor > 0) {
      return {
        contractVersion: payload.contractVersion,
        events: [],
        nextCursor: cursor,
        reset: false,
        truncated: false,
        badLineCount: 0,
      };
    }
    return payload;
  }
  return callBridge('bridge_tail_events', {
    rootDir: settings.rootDir,
    jobId,
    cursor,
    maxBytes,
    maxLines,
  });
}

export async function startAssistantTurn(
  settings: PanelSettings,
  options: AssistantStartTurnOptions,
): Promise<AssistantStartTurnResponse> {
  if (isBridgePreviewMode()) {
    return previewAssistantStartTurn(options.assistantTurnId, options.sessionId);
  }
  return callBridge('bridge_assistant_start_turn', {
    config: toBridgeConfig(settings, 120000),
    assistantTurnId: options.assistantTurnId,
    sessionId: options.sessionId,
    userMessage: options.userMessage,
    compiledPrompt: options.compiledPrompt,
    provider: options.provider,
    providerId: options.providerId,
    fallbackProvider: options.fallbackProvider,
    fallbackProviderId: options.fallbackProviderId,
    model: options.model,
    hfModelId: options.hfModelId,
  });
}

export async function searchAssistantSystemKnowledge(
  settings: PanelSettings,
  query: string,
): Promise<AssistantKnowledgeSearchResponse> {
  if (isBridgePreviewMode()) {
    return previewAssistantKnowledgeSearch(query);
  }
  return normalizeAssistantKnowledgeSearchResponse(
    await callBridge('bridge_assistant_knowledge_search', {
      config: toBridgeConfig(settings, 30000),
      query,
      maxHits: 8,
      maxContextChars: 8000,
    }),
  );
}

export async function planAssistantTask(
  settings: PanelSettings,
  options: AssistantTaskPlanOptions,
): Promise<AssistantTaskPlan> {
  if (isBridgePreviewMode()) {
    return previewAssistantTaskPlan(options.message);
  }
  return normalizeAssistantTaskPlan(
    await callBridge('bridge_assistant_task_plan', {
      config: toBridgeConfig(settings, 30000),
      message: options.message,
      operatorId: options.operatorId,
      workspaceId: options.workspaceId,
      agentHint: options.agentHint,
    }),
  );
}

export async function submitAssistantTask(
  settings: PanelSettings,
  options: AssistantTaskSubmitOptions,
): Promise<AssistantTaskSubmissionResult> {
  if (isBridgePreviewMode()) {
    return previewAssistantTaskSubmission(options);
  }
  return normalizeAssistantTaskSubmissionResult(
    await callBridge('bridge_assistant_task_submit', {
      config: toBridgeConfig(settings, 30000),
      proposalId: options.proposalId,
      confirmPlanHash: options.confirmPlanHash,
      operatorId: options.operatorId,
    }),
  );
}

export async function fetchLocalProductReadiness(
  settings: PanelSettings,
  target = 'auto',
): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewLocalProductReadiness(target === 'auto' ? 'windows-x64' : target);
  }
  return callBridge('bridge_local_product_readiness', {
    config: toBridgeConfig(settings, 30000),
    target,
  });
}

export async function fetchLocalProductMatrix(
  settings: PanelSettings,
  includeExperimental = false,
): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewLocalProductMatrix();
  }
  return callBridge('bridge_local_product_matrix', {
    config: toBridgeConfig(settings, 30000),
    includeExperimental,
  });
}

export async function fetchPlatformEvidenceStatus(settings: PanelSettings): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewPlatformEvidenceStatus();
  }
  return callBridge('bridge_local_product_platform_evidence_status', {
    config: toBridgeConfig(settings, 30000),
  });
}

export async function fetchRcHandoffStatus(settings: PanelSettings): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return previewRcHandoffStatus();
  }
  return callBridge('bridge_local_product_rc_handoff_status', {
    config: toBridgeConfig(settings, 30000),
  });
}

export async function getAssistantTaskStatus(settings: PanelSettings, proposalId: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    const plan = previewAssistantTaskPlan('Preview governed assistant task');
    return {
      schemaVersion: 'assistant-tasking.status/v1',
      proposalId,
      status: 'planned',
      plan: { ...plan, proposalId },
      submission: null,
      evidenceRefs: plan.evidenceExpectation.expectedRefs,
      blockingReasons: [],
    };
  }
  return callBridge('bridge_assistant_task_status', {
    config: toBridgeConfig(settings, 30000),
    proposalId,
  });
}

export async function explainAssistantTask(settings: PanelSettings, proposalId: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return {
      schemaVersion: 'assistant-tasking.status/v1',
      proposalId,
      status: 'planned',
      plan: previewAssistantTaskPlan('Preview governed assistant task'),
      submission: null,
      evidenceRefs: ['artifacts/assistant-tasking/proposals/astp_preview_write_fixture.json'],
      blockingReasons: [],
    };
  }
  return callBridge('bridge_assistant_task_explain', {
    config: toBridgeConfig(settings, 30000),
    proposalId,
  });
}

export async function cancelAssistantTurn(
  _settings: PanelSettings,
  assistantTurnId: string,
): Promise<AssistantCancelTurnResponse> {
  if (isBridgePreviewMode()) {
    return {
      contractVersion: '2.0',
      assistantTurnId,
      sessionId: 'preview-session',
      processId: null,
      status: 'cancelled',
    };
  }
  return callBridge('bridge_assistant_cancel_turn', {
    assistantTurnId,
  });
}

export async function listAssistantModels(
  settings: PanelSettings,
  request: AssistantProviderModelsRequest,
): Promise<AssistantProviderModelsResponse> {
  if (isBridgePreviewMode()) {
    const payload = previewAssistantProviderModels(request.profile || settings.profile);
    if (request.provider && request.provider !== 'all' && request.provider !== 'auto') {
      return {
        ...payload,
        provider: request.provider,
        providers: payload.providers.filter(
          (item) => item.provider === request.provider || item.legacyProvider === request.provider,
        ),
      };
    }
    return payload;
  }
  return callBridge('bridge_assistant_provider_models', {
    config: toBridgeConfig(settings, 15000),
    profile: request.profile,
    provider: request.provider,
    refresh: request.refresh,
  });
}

export async function listenAssistantEvents(
  handler: (event: AssistantStreamEvent) => void,
): Promise<AssistantEventUnlisten> {
  if (!isTauriRuntime()) {
    return () => undefined;
  }
  const unlisten = await listen<AssistantStreamEvent>('assistant://event', (event) => {
    handler(event.payload);
  });
  return unlisten;
}
