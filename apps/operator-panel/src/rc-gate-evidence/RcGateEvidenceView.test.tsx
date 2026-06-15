import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { RcGateEvidenceView } from './RcGateEvidenceView';

describe('RcGateEvidenceView', () => {
  it('renders ready gate evidence without raw payloads', () => {
    render(
      <RcGateEvidenceView
        snapshot={{
          schemaVersion: 'control-plane.rc-gate-evidence-snapshot/v1',
          status: 'ready',
          target: 'mainline-rc',
          latestLedgerRef: 'artifacts/release-gates/mainline-rc/gate_evidence_ledger.json',
          latestVerificationRef: 'artifacts/release-gates/mainline-rc/gate_evidence_verification.json',
          verifiedGateCount: 10,
          missingGateCount: 0,
          missingArtifactCount: 0,
          secretScanStatus: 'pass',
          rawMarkerScanStatus: 'pass',
          platform: 'windows',
          makeRequired: false,
          readyForRcFreeze: true,
          blockingReasons: [],
          warnings: [],
        }}
      />,
    );

    const view = screen.getByTestId('rc-gate-evidence');
    expect(view).toHaveTextContent('ready');
    expect(view).toHaveTextContent('mainline-rc');
    expect(view).toHaveTextContent('10');
    expect(view).toHaveTextContent('Make required: no');
    expect(view).toHaveTextContent('Ready for RC freeze: yes');
    expect(view).not.toHaveTextContent('rawPayload');
    expect(view).not.toHaveTextContent('BEGIN RAW');
  });

  it('renders missing fallback fail-closed', () => {
    render(<RcGateEvidenceView snapshot={null} />);

    const view = screen.getByTestId('rc-gate-evidence');
    expect(view).toHaveTextContent('missing');
    expect(view).toHaveTextContent('RC_GATE_EVIDENCE_LEDGER_MISSING');
    expect(view).toHaveTextContent('Ready for RC freeze: no');
  });
});
