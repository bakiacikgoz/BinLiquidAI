import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ReleaseDecisionView } from './ReleaseDecisionView';

describe('ReleaseDecisionView', () => {
  it('renders conditional signoff state without raw JSON', () => {
    render(
      <ReleaseDecisionView
        snapshot={{
          schemaVersion: 'control-plane.rc-release-decision-snapshot/v1',
          status: 'conditional',
          latestDossierRef: 'artifacts/rc-release-decision/release_decision_dossier.json',
          latestSummaryRef: 'artifacts/rc-release-decision/release_decision_summary.md',
          signoffStatus: 'missing',
          hatAStatus: 'conditional',
          hatBStatus: 'blocked_external_credentials',
          designPartnerRcStatus: 'conditional',
          noShipBlockingCount: 0,
          externalBlockerCount: 2,
          evidenceRefCount: 2,
          blockingReasons: [],
          warnings: ['CONDITIONAL_RELEASE_DECISION'],
        }}
      />,
    );

    expect(screen.getByText('RC Release Decision')).toBeInTheDocument();
    expect(screen.getByText('signoff:missing')).toBeInTheDocument();
    expect(screen.queryByText(/rawPayload/i)).not.toBeInTheDocument();
  });
});
