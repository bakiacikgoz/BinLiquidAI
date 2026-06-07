import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { EvidencePackSummary } from '../../control-plane/types';
import { renderOperatorPanel } from '../../test/render';
import { EvidencePackView } from './EvidencePackView';

const evidencePack: EvidencePackSummary = {
  artifactCount: 9,
  blockingReasons: ['QUALIFICATION_REPORT_MISSING'],
  claimGuardStatus: 'conditional',
  createdAtUtc: '2026-06-01T12:00:00Z',
  exportPath: 'artifacts/control-plane/evidence/evp-preview-run',
  hashChainStatus: 'valid',
  packId: 'evp-preview-run',
  redactionStatus: 'passed',
  replayStatus: 'passed',
  runId: 'cp-run-preview',
  signatureStatus: 'valid',
};

describe('EvidencePackView', () => {
  it('renders evidence pack verification state and invokes verification', async () => {
    const onVerify = vi.fn();
    const { user } = renderOperatorPanel(
      <EvidencePackView
        evidencePacks={[evidencePack]}
        verifyResult={{
          blocking_reasons: ['EVIDENCE_HASH_MISMATCH'],
          hash_chain_verified: false,
          replay_verified: true,
          signature_verified: true,
          status: 'fail',
        }}
        locale="tr"
        onVerify={onVerify}
      />,
    );

    expect(screen.getByRole('heading', { name: 'Kanıt paketleri' })).toBeInTheDocument();
    expect(screen.getByText('evp-preview-run')).toBeInTheDocument();
    expect(screen.getByText(/EVIDENCE_HASH_MISMATCH/)).toHaveTextContent('hash zinciri');
    expect(screen.getByText('başarısız')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Sonuncuyu doğrula' }));

    expect(onVerify).toHaveBeenCalledTimes(1);
  });

  it('disables verification when no manifest path is available', () => {
    renderOperatorPanel(
      <EvidencePackView
        evidencePacks={[]}
        verifyDisabledReason="No evidence manifest is available to verify."
        verifyResult={null}
        onVerify={vi.fn()}
      />,
    );

    expect(screen.getByRole('button', { name: 'Verify latest' })).toBeDisabled();
    expect(screen.getByText('No evidence manifest is available to verify.')).toBeInTheDocument();
  });
});
