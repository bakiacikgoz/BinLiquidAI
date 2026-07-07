import { describe, expect, it } from 'vitest';

import { getTargetClaimBadge, mapLocalProductReadiness } from './localProductMappers';

describe('local product readiness mappers', () => {
  it('maps supported and not-evidenced claim boundaries', () => {
    const vm = mapLocalProductReadiness({
      schemaVersion: 'local_product_readiness/v1',
      overallStatus: 'pass',
      target: {
        os: 'windows',
        arch: 'x64',
        targetId: 'windows-x64',
        supportTier: 'supported',
        claimAllowed: true,
        reasonCodes: [],
      },
      claimBoundary: {
        claimAllowed: true,
        supportedClaims: ['windows-x64'],
        notEvidencedTargets: ['darwin-arm64', 'darwin-x64', 'linux-x64'],
        unsupportedTargets: [],
        blockedTargets: [],
        productClaimSummary: 'Claims are limited to windows-x64.',
        blockingReasons: [],
      },
    });

    expect(vm.currentTarget.targetId).toBe('windows-x64');
    expect(vm.supportedClaims).toEqual(['windows-x64']);
    expect(vm.notEvidencedTargets).toContain('darwin-arm64');
    expect(getTargetClaimBadge(vm.currentTarget)).toBe('supported');
  });
});

