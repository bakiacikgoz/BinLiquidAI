import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { GovernedPilotWorkflowView } from './GovernedPilotWorkflowView';

describe('GovernedPilotWorkflowView', () => {
  it('renders deterministic pilot closure without raw payloads', () => {
    render(
      <GovernedPilotWorkflowView
        snapshot={{
          schemaVersion: 'control-plane.governed-pilot-workflow/v1',
          generatedAtUtc: '2026-06-14T00:00:00Z',
          enabled: true,
          status: 'pass',
          workflowId: 'enterprise-governed-memory-provider',
          runId: 'enterprise-governed-memory-provider-20260614000000',
          mode: 'deterministic',
          evidenceMode: 'hash_only',
          rawPersistence: false,
          claimGuardStatus: 'pass',
          blockedClaims: ['public-desktop-installer', 'live-macos-computer-use'],
          latestReportPath: 'artifacts/governed-pilot-workflow/latest/report.json',
          latestSummaryPath: 'artifacts/governed-pilot-workflow/latest/REPORT.md',
          verifierStatus: 'pass',
          blockingReasons: [],
          warnings: [],
        }}
      />,
    );

    expect(screen.getByTestId('governed-pilot-workflow')).toHaveTextContent('hash_only');
    expect(screen.getByTestId('governed-pilot-workflow')).toHaveTextContent('public-desktop-installer');
    expect(screen.getByTestId('governed-pilot-workflow')).toHaveTextContent('false');
    expect(screen.queryByText('Draft a remediation plan')).not.toBeInTheDocument();
  });

  it('renders missing state before workflow proof exists', () => {
    render(<GovernedPilotWorkflowView snapshot={null} />);

    expect(screen.getByTestId('governed-pilot-workflow')).toHaveTextContent('not run');
    expect(screen.getByTestId('governed-pilot-workflow')).toHaveTextContent('hash_only');
  });
});
