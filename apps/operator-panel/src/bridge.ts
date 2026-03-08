import { invoke } from '@tauri-apps/api/core';

import type { PanelSettings } from './settings';

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

export class BridgeError extends Error {
  readonly payload: BridgeErrorPayload;

  constructor(payload: BridgeErrorPayload) {
    super(payload.message);
    this.name = 'BridgeError';
    this.payload = payload;
  }
}

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
  events: unknown[];
  nextCursor: number;
  reset: boolean;
  truncated: boolean;
  badLineCount: number;
}

type PreviewRunStatus = 'running' | 'blocked' | 'completed';

const PREVIEW_APPROVALS = [
  {
    approval_id: 'apr_20260308_policy_gate',
    status: 'pending',
    requested_at: '2026-03-08T09:31:00Z',
    reason_code: 'POLICY_EXCEPTION',
    summary: 'Approval required for external export of audit envelope',
    actor: 'router:policy',
  },
  {
    approval_id: 'apr_20260308_exec_override',
    status: 'pending',
    requested_at: '2026-03-08T09:18:00Z',
    reason_code: 'EXECUTION_OVERRIDE',
    summary: 'Operator confirmation needed before privileged replay execution',
    actor: 'supervisor:execution',
  },
] as const;

const PREVIEW_RUNS: Array<{ job_id: string; status: PreviewRunStatus; started_at: string; updated_at: string }> = [
  {
    job_id: 'run_20260308_0910',
    status: 'running',
    started_at: '2026-03-08T09:10:00Z',
    updated_at: '2026-03-08T09:35:00Z',
  },
  {
    job_id: 'run_20260308_0838',
    status: 'blocked',
    started_at: '2026-03-08T08:38:00Z',
    updated_at: '2026-03-08T09:12:00Z',
  },
  {
    job_id: 'run_20260307_2214',
    status: 'completed',
    started_at: '2026-03-07T22:14:00Z',
    updated_at: '2026-03-07T22:26:00Z',
  },
];

const PREVIEW_EVENTS = [
  {
    timestamp: '2026-03-08T09:10:12Z',
    event: 'router_decision',
    data: {
      path: 'team',
      policy: 'balanced',
      confidence: 0.91,
    },
  },
  {
    timestamp: '2026-03-08T09:10:27Z',
    event: 'expert_start',
    data: {
      expert: 'code_expert',
      task: 'Validate operator replay envelope',
    },
  },
  {
    timestamp: '2026-03-08T09:11:05Z',
    event: 'approval_pending',
    data: {
      approval_id: 'apr_20260308_policy_gate',
      actor: 'router:policy',
    },
  },
] as const;

function toBridgeConfig(settings: PanelSettings): BridgeConfig {
  return {
    mode: settings.mode,
    cliPath: settings.cliPath.trim() || undefined,
    bundledPythonPath: settings.bundledPythonPath.trim() || undefined,
    profile: settings.profile,
    rootDir: settings.rootDir,
    env: {
      BINLIQUID_PROFILE_NAME: settings.profile,
    },
    timeoutMs: 15000,
  };
}

function isTauriRuntime(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

export function isBridgePreviewMode(): boolean {
  return !isTauriRuntime();
}

async function callBridge<T>(command: string, args: Record<string, unknown>): Promise<T> {
  const result = await invoke<BridgeResult<T>>(command, args);
  if (!result.ok) {
    throw new BridgeError(result.error);
  }
  return result.data;
}

function previewCommands() {
  return {
    teamListJson: true,
    teamReplayJson: true,
    approvalShowJson: true,
    approvalPendingJson: true,
    approvalDecide: true,
    approvalExecute: true,
  };
}

function getPreviewHandshake(settings: PanelSettings) {
  return {
    uiVersion: '0.5.0-beta.1',
    coreVersion: '0.5.0-preview',
    contractVersion: '2.0',
    capabilities: {
      contractVersion: '2.0',
      previewMode: true,
      commands: previewCommands(),
    },
    doctor: {
      runtime: 'browser-preview',
      profile: settings.profile,
      status: 'ok',
      note: 'Mock bridge data is active because the Tauri runtime is not attached.',
    },
  };
}

function getPreviewApprovals(settings: PanelSettings) {
  return {
    pending: PREVIEW_APPROVALS.map((item) => ({
      ...item,
      profile: settings.profile,
    })),
  };
}

function getPreviewApprovalDetail(settings: PanelSettings, approvalId: string) {
  const approval = PREVIEW_APPROVALS.find((item) => item.approval_id === approvalId) ?? PREVIEW_APPROVALS[0];
  return {
    ...approval,
    profile: settings.profile,
    previewMode: true,
    requested_by: approval.actor,
    command_hint: `binliquid approval show ${approval.approval_id} --json`,
    summary: {
      target: 'audit_envelope.json',
      scope: 'enterprise qualification run',
      risk: 'medium',
    },
  };
}

function getPreviewRuns(settings: PanelSettings) {
  return {
    items: PREVIEW_RUNS.map((item) => ({
      ...item,
      profile: settings.profile,
    })),
  };
}

function getPreviewRunStatus(settings: PanelSettings, jobId: string) {
  const run = PREVIEW_RUNS.find((item) => item.job_id === jobId) ?? PREVIEW_RUNS[0];
  return {
    job: {
      ...run,
      profile: settings.profile,
      root_dir: settings.rootDir,
    },
    summary: {
      approvals_pending: run.status === 'blocked' ? 1 : 0,
      artifacts_ready: 4,
      policy: settings.profile,
    },
  };
}

function getPreviewRunReplay(settings: PanelSettings, jobId: string) {
  return {
    job_id: jobId,
    profile: settings.profile,
    previewMode: true,
    replay: [
      {
        phase: 'plan',
        actor: 'planner',
        status: 'completed',
      },
      {
        phase: 'execute',
        actor: 'code_expert',
        status: 'running',
      },
      {
        phase: 'governance',
        actor: 'policy',
        status: 'pending',
      },
    ],
  };
}

function getPreviewArtifact(jobId: string, artifactName: string) {
  const payloads: Record<string, unknown> = {
    'status.json': {
      job_id: jobId,
      status: 'running',
      updated_at: '2026-03-08T09:35:00Z',
      approvals_pending: 1,
    },
    'tasks.json': {
      tasks: [
        { id: 'task-01', state: 'done', title: 'Assemble replay context' },
        { id: 'task-02', state: 'running', title: 'Validate audit envelope' },
      ],
    },
    'handoffs.json': {
      handoffs: [
        { from: 'planner', to: 'code_expert', status: 'accepted' },
        { from: 'code_expert', to: 'policy', status: 'waiting' },
      ],
    },
    'audit_envelope.json': {
      audit_id: 'audit_20260308_preview',
      integrity: 'verified',
      export_ready: false,
    },
  };

  return {
    artifactName,
    previewMode: true,
    payload: payloads[artifactName] ?? {},
  };
}

function getPreviewTailEvents(cursor: number): TailEventsResponse {
  if (cursor > 0) {
    return {
      events: [],
      nextCursor: cursor,
      reset: false,
      truncated: false,
      badLineCount: 0,
    };
  }

  return {
    events: [...PREVIEW_EVENTS],
    nextCursor: 1872,
    reset: false,
    truncated: false,
    badLineCount: 0,
  };
}

export async function handshake(settings: PanelSettings): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return getPreviewHandshake(settings);
  }
  return callBridge('bridge_handshake', { config: toBridgeConfig(settings) });
}

export async function fetchApprovals(settings: PanelSettings): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return getPreviewApprovals(settings);
  }
  return callBridge('bridge_approval_pending', { config: toBridgeConfig(settings) });
}

export async function showApproval(settings: PanelSettings, approvalId: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return getPreviewApprovalDetail(settings, approvalId);
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
      ok: true,
      previewMode: true,
      approvalId,
      approve,
      operatorId,
      reason,
      profile: settings.profile,
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
      ok: true,
      previewMode: true,
      approvalId,
      operatorId,
      profile: settings.profile,
    };
  }
  return callBridge('bridge_approval_execute', {
    config: toBridgeConfig(settings),
    approvalId,
    operatorId,
  });
}

export async function listRuns(settings: PanelSettings, since?: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return {
      ...getPreviewRuns(settings),
      since,
    };
  }
  return callBridge('bridge_team_list', {
    config: toBridgeConfig(settings),
    since,
  });
}

export async function getRunStatus(settings: PanelSettings, jobId: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return getPreviewRunStatus(settings, jobId);
  }
  return callBridge('bridge_team_status', {
    config: toBridgeConfig(settings),
    jobId,
  });
}

export async function getRunReplay(settings: PanelSettings, jobId: string): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return getPreviewRunReplay(settings, jobId);
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
      ok: true,
      previewMode: true,
      jobId,
      exportDir,
      profile: settings.profile,
    };
  }
  return callBridge('bridge_team_export', {
    config: toBridgeConfig(settings),
    jobId,
    exportDir,
  });
}

export async function readArtifact(
  settings: PanelSettings,
  jobId: string,
  artifactName: string,
  maxBytes = 256 * 1024,
): Promise<unknown> {
  if (isBridgePreviewMode()) {
    return getPreviewArtifact(jobId, artifactName);
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
    return getPreviewTailEvents(cursor);
  }
  return callBridge('bridge_tail_events', {
    rootDir: settings.rootDir,
    jobId,
    cursor,
    maxBytes,
    maxLines,
  });
}
