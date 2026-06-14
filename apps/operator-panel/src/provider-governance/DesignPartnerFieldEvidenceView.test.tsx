import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DesignPartnerFieldEvidenceView } from './DesignPartnerFieldEvidenceView';

describe('DesignPartnerFieldEvidenceView', () => {
  it('renders ready field evidence without raw payloads', () => {
    render(
      <DesignPartnerFieldEvidenceView
        snapshot={{
          schemaVersion: 'control-plane.design-partner-field-evidence/v1',
          generatedAtUtc: '2026-06-14T00:00:00Z',
          status: 'ready',
          mode: 'target_environment',
          sessionId: 'field-session',
          evidenceMode: 'hash_only',
          rawPersistence: false,
          attestationStatus: 'valid',
          strictRcStatus: 'ready',
          itemCount: 6,
          blockedClaims: ['public-desktop-installer', 'live-macos-computer-use'],
          latestBundlePath: 'artifacts/design-partner-field-evidence/target_evidence_bundle.json',
          latestAttestationPath: 'artifacts/design-partner-field-evidence/attestation_validation.json',
          latestPromotionPath: 'artifacts/design-partner-field-evidence/strict_rc_promotion.json',
          blockingReasons: [],
          warnings: [],
        }}
      />,
    );

    const view = screen.getByTestId('design-partner-field-evidence');
    expect(view).toHaveTextContent('hash_only');
    expect(view).toHaveTextContent('attestation_valid');
    expect(view).toHaveTextContent('strict_rc_ready');
    expect(view).toHaveTextContent('public-desktop-installer');
    expect(view).not.toHaveTextContent('BEGIN RAW');
  });

  it('renders missing state before field evidence is collected', () => {
    render(<DesignPartnerFieldEvidenceView snapshot={null} />);

    expect(screen.getByTestId('design-partner-field-evidence')).toHaveTextContent('not collected');
    expect(screen.getByTestId('design-partner-field-evidence')).toHaveTextContent('FIELD_EVIDENCE_NOT_COLLECTED');
  });
});
