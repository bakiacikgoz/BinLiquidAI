const REQUIRED_COMMAND_KEYS = [
  'approvalShowJson',
  'approvalPendingJson',
  'approvalDecide',
  'approvalExecute',
  'authWhoamiJson',
  'authCheckJson',
  'backupCreateJson',
  'backupVerifyJson',
  'computerUseSubmit',
  'computerUsePause',
  'computerUseResume',
  'computerUseStop',
  'computerUseStateJson',
  'configResolveJson',
  'gaReadinessJson',
  'keysStatusJson',
  'keysVerifyJson',
  'keysRotatePlanJson',
  'metricsSnapshotJson',
  'migratePlanJson',
  'migrateApplyDryRunJson',
  'qualificationRunJson',
  'restoreVerifyJson',
  'securityBaselineJson',
  'supportBundleExportJson',
  'teamSubmit',
  'teamResumeSubmit',
  'teamListJson',
  'teamStatusJson',
  'teamReplayJson',
] as const;

export type ComputerUseCapability = {
  enabled: boolean;
  stage: string;
  platform: string;
  scope: string;
  executionModes: string[];
  replayable: boolean;
  failClosed: boolean;
  adapterStatus: string;
  reasonCode: string | null;
  summary: string | null;
};

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}

function readString(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  return typeof value === 'string' ? value : null;
}

function readBoolean(source: Record<string, unknown>, key: string): boolean {
  return source[key] === true;
}

function readStringArray(source: Record<string, unknown>, key: string): string[] {
  const value = source[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

export function hasContractMismatch(handshakeData: unknown): boolean {
  if (!handshakeData) {
    return false;
  }

  const handshake = asRecord(handshakeData);
  const capabilities = asRecord(handshake.capabilities);
  const commandCapabilities = asRecord(capabilities.commands);

  if (readString(capabilities, 'contractVersion') !== '2.0') {
    return true;
  }

  return REQUIRED_COMMAND_KEYS.some((key) => commandCapabilities[key] !== true);
}

export function getComputerUseCapability(handshakeData: unknown): ComputerUseCapability {
  const handshake = asRecord(handshakeData);
  const capabilities = asRecord(handshake.capabilities);
  const features = asRecord(capabilities.features);
  const computerUse = asRecord(features.computerUsePilot);

  return {
    enabled: readBoolean(computerUse, 'enabled'),
    stage: readString(computerUse, 'stage') ?? 'unknown',
    platform: readString(computerUse, 'platform') ?? 'unknown',
    scope: readString(computerUse, 'scope') ?? 'unknown',
    executionModes: readStringArray(computerUse, 'executionModes'),
    replayable: readBoolean(computerUse, 'replayable'),
    failClosed: readBoolean(computerUse, 'failClosed'),
    adapterStatus: readString(computerUse, 'adapterStatus') ?? 'unknown',
    reasonCode: readString(computerUse, 'reasonCode'),
    summary: readString(computerUse, 'summary'),
  };
}

export function isComputerUseLiveEnabled(handshakeData: unknown): boolean {
  const capability = getComputerUseCapability(handshakeData);
  return capability.enabled === true && capability.failClosed === true;
}
