import { describe, expect, it } from 'vitest';

import {
  getComputerUseCapability,
  getComputerUseVisionRuntimeCapability,
  hasContractMismatch,
  isComputerUseLiveEnabled,
  isComputerUseVisionRuntimeLiveEnabled,
} from './capabilities';

const baseCommands = {
  computerUseSubmit: true,
  computerUsePause: true,
  computerUseResume: true,
  computerUseStop: true,
  computerUseStateJson: true,
  teamSubmit: true,
  teamResumeSubmit: true,
  teamListJson: true,
  teamStatusJson: true,
  teamReplayJson: true,
  approvalShowJson: true,
  approvalPendingJson: true,
  approvalDecide: true,
  approvalExecute: true,
  configResolveJson: true,
  authWhoamiJson: true,
  authCheckJson: true,
  securityBaselineJson: true,
  keysStatusJson: true,
  keysVerifyJson: true,
  keysRotatePlanJson: true,
  supportBundleExportJson: true,
  metricsSnapshotJson: true,
  gaReadinessJson: true,
  qualificationRunJson: true,
  backupCreateJson: true,
  backupVerifyJson: true,
  restoreVerifyJson: true,
  migratePlanJson: true,
  migrateApplyDryRunJson: true,
};

const enabledComputerUse = {
  enabled: true,
  stage: 'execution_slice',
  platform: 'macos',
  scope: 'browser+desktop+file',
  executionModes: ['dry_run', 'step_approval', 'execute'],
  replayable: true,
  failClosed: true,
  adapterStatus: 'safari_applescript',
  reasonCode: 'MACOS_COMPUTER_USE_PILOT',
  summary: 'macOS pilot is enabled.',
};

const visionRuntime = {
  enabled: false,
  stage: 'not_qualified',
  platform: 'windows',
  scope: 'vision_first_desktop_web_file',
  executionModes: ['dry_run', 'step_approval'],
  replayable: true,
  failClosed: true,
  reasonCode: 'WINDOWS_COMPUTER_USE_NOT_QUALIFIED',
  summary: 'Vision runtime is not qualified on Windows.',
  provider: {
    kind: 'none',
    configured: false,
    model: null,
  },
  safety: {
    rawScreenshotPersistence: 'disabled',
    terminalControl: 'deny',
    approvalRequiredForRiskyActions: true,
  },
};

describe('capability handshake validation', () => {
  it('accepts fully compatible capabilities', () => {
    expect(
      hasContractMismatch({
        capabilities: {
          contractVersion: '2.0',
          commands: baseCommands,
        },
      }),
    ).toBe(false);
  });

  it('rejects mismatched contract version', () => {
    expect(
      hasContractMismatch({
        capabilities: {
          contractVersion: '1.0',
          commands: baseCommands,
        },
      }),
    ).toBe(true);
  });

  it('rejects when required command flags are missing', () => {
    expect(
      hasContractMismatch({
        capabilities: {
          contractVersion: '2.0',
          commands: {
            ...baseCommands,
            approvalExecute: false,
          },
        },
      }),
    ).toBe(true);
  });

  it('rejects when enterprise command flags are missing', () => {
    expect(
      hasContractMismatch({
        capabilities: {
          contractVersion: '2.0',
          commands: {
            ...baseCommands,
            supportBundleExportJson: false,
          },
        },
      }),
    ).toBe(true);
  });

  it('reads computer-use capability details', () => {
    expect(
      getComputerUseCapability({
        capabilities: {
          features: {
            computerUsePilot: enabledComputerUse,
          },
        },
      }),
    ).toEqual(enabledComputerUse);
  });

  it('enables live computer-use only when the fail-closed pilot is enabled', () => {
    expect(
      isComputerUseLiveEnabled({
        capabilities: {
          features: {
            computerUsePilot: enabledComputerUse,
          },
        },
      }),
    ).toBe(true);
  });

  it('keeps Windows computer-use disabled and exposes the reason code', () => {
    const capability = getComputerUseCapability({
      capabilities: {
        features: {
          computerUsePilot: {
            ...enabledComputerUse,
            enabled: false,
            stage: 'not_qualified',
            platform: 'windows',
            scope: 'core+operator_panel+bundled_runtime',
            executionModes: [],
            adapterStatus: 'windows_scaffold',
            reasonCode: 'WINDOWS_COMPUTER_USE_NOT_QUALIFIED',
            summary: 'Windows live computer-use is not qualified.',
          },
        },
      },
    });

    expect(capability.enabled).toBe(false);
    expect(capability.reasonCode).toBe('WINDOWS_COMPUTER_USE_NOT_QUALIFIED');
    expect(isComputerUseLiveEnabled({ capabilities: { features: { computerUsePilot: capability } } })).toBe(false);
  });

  it('reads additive vision runtime capability without enabling live execution', () => {
    const capability = getComputerUseVisionRuntimeCapability({
      capabilities: {
        features: {
          computerUseVisionRuntime: visionRuntime,
        },
      },
    });

    expect(capability).toEqual(visionRuntime);
    expect(
      isComputerUseVisionRuntimeLiveEnabled({
        capabilities: { features: { computerUseVisionRuntime: visionRuntime } },
      }),
    ).toBe(false);
  });
});
