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

async function callBridge<T>(command: string, args: Record<string, unknown>): Promise<T> {
  if (!isTauriRuntime()) {
    throw new BridgeError({
      code: 'CLI_FAILED',
      message: 'Tauri runtime not available',
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

export async function handshake(settings: PanelSettings): Promise<unknown> {
  return callBridge('bridge_handshake', { config: toBridgeConfig(settings) });
}

export async function fetchApprovals(settings: PanelSettings): Promise<unknown> {
  return callBridge('bridge_approval_pending', { config: toBridgeConfig(settings) });
}

export async function showApproval(settings: PanelSettings, approvalId: string): Promise<unknown> {
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
  return callBridge('bridge_approval_execute', {
    config: toBridgeConfig(settings),
    approvalId,
    operatorId,
  });
}

export async function listRuns(settings: PanelSettings, since?: string): Promise<unknown> {
  return callBridge('bridge_team_list', {
    config: toBridgeConfig(settings),
    since,
  });
}

export async function getRunStatus(settings: PanelSettings, jobId: string): Promise<unknown> {
  return callBridge('bridge_team_status', {
    config: toBridgeConfig(settings),
    jobId,
  });
}

export async function getRunReplay(settings: PanelSettings, jobId: string): Promise<unknown> {
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
  return callBridge('bridge_tail_events', {
    rootDir: settings.rootDir,
    jobId,
    cursor,
    maxBytes,
    maxLines,
  });
}
