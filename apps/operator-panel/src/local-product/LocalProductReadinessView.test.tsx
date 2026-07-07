import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { LocalProductReadinessView } from './LocalProductReadinessView';

describe('LocalProductReadinessView', () => {
  it('shows current machine, supported claims, and not-evidenced targets', () => {
    render(
      <LocalProductReadinessView
        report={{
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
            productClaimSummary: 'Claims are limited to evidenced targets.',
            blockingReasons: [],
          },
        }}
      />,
    );

    expect(screen.getByText('Local Product Readiness')).toBeInTheDocument();
    expect(screen.getAllByText('windows-x64').length).toBeGreaterThan(0);
    expect(screen.getByText('darwin-arm64')).toBeInTheDocument();
    expect(screen.getByText(/Claims are limited/)).toBeInTheDocument();
  });
});
