import { describe, expect, it } from 'vitest';

import { hasContractMismatch } from './capabilities';

const baseCommands = {
  teamListJson: true,
  teamReplayJson: true,
  approvalShowJson: true,
  approvalPendingJson: true,
  approvalDecide: true,
  approvalExecute: true,
};

describe('capability handshake validation', () => {
  it('accepts fully compatible capabilities', () => {
    expect(
      hasContractMismatch({
        capabilities: {
          contractVersion: '1.0',
          commands: baseCommands,
        },
      }),
    ).toBe(false);
  });

  it('rejects mismatched contract version', () => {
    expect(
      hasContractMismatch({
        capabilities: {
          contractVersion: '2.0',
          commands: baseCommands,
        },
      }),
    ).toBe(true);
  });

  it('rejects when required command flags are missing', () => {
    expect(
      hasContractMismatch({
        capabilities: {
          contractVersion: '1.0',
          commands: {
            ...baseCommands,
            approvalExecute: false,
          },
        },
      }),
    ).toBe(true);
  });
});
