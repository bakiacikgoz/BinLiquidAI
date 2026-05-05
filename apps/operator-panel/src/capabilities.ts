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

export type ComputerUseVisionRuntimeCapability = {
  enabled: boolean;
  stage: string;
  platform: string;
  scope: string;
  executionModes: string[];
  replayable: boolean;
  failClosed: boolean;
  reasonCode: string | null;
  summary: string | null;
  provider: {
    kind: string;
    configured: boolean;
    model: string | null;
  };
  safety: {
    rawScreenshotPersistence: string;
    terminalControl: string;
    approvalRequiredForRiskyActions: boolean;
  };
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

export function getComputerUseVisionRuntimeCapability(
  handshakeData: unknown,
): ComputerUseVisionRuntimeCapability {
  const handshake = asRecord(handshakeData);
  const capabilities = asRecord(handshake.capabilities);
  const features = asRecord(capabilities.features);
  const computerUse = asRecord(features.computerUseVisionRuntime);
  const provider = asRecord(computerUse.provider);
  const safety = asRecord(computerUse.safety);

  return {
    enabled: readBoolean(computerUse, 'enabled'),
    stage: readString(computerUse, 'stage') ?? 'not_configured',
    platform: readString(computerUse, 'platform') ?? 'unknown',
    scope: readString(computerUse, 'scope') ?? 'vision_first_desktop_web_file',
    executionModes: readStringArray(computerUse, 'executionModes'),
    replayable: readBoolean(computerUse, 'replayable'),
    failClosed: readBoolean(computerUse, 'failClosed'),
    reasonCode: readString(computerUse, 'reasonCode'),
    summary: readString(computerUse, 'summary'),
    provider: {
      kind: readString(provider, 'kind') ?? 'none',
      configured: readBoolean(provider, 'configured'),
      model: readString(provider, 'model'),
    },
    safety: {
      rawScreenshotPersistence: readString(safety, 'rawScreenshotPersistence') ?? 'disabled',
      terminalControl: readString(safety, 'terminalControl') ?? 'deny',
      approvalRequiredForRiskyActions: readBoolean(safety, 'approvalRequiredForRiskyActions'),
    },
  };
}

export function isComputerUseLiveEnabled(handshakeData: unknown): boolean {
  const capability = getComputerUseCapability(handshakeData);
  return capability.enabled === true && capability.failClosed === true;
}

export function isComputerUseVisionRuntimeLiveEnabled(handshakeData: unknown): boolean {
  const capability = getComputerUseVisionRuntimeCapability(handshakeData);
  return capability.enabled === true && capability.failClosed === true;
}
