import { describe, expect, it } from 'vitest';

import { mapRcGateEvidence } from './rcGateEvidenceMappers';

describe('mapRcGateEvidence', () => {
  it('normalizes missing snapshot as fail-closed', () => {
    const summary = mapRcGateEvidence(null);

    expect(summary.status).toBe('missing');
    expect(summary.readyForRcFreeze).toBe(false);
    expect(summary.warnings).toContain('RC_GATE_EVIDENCE_LEDGER_MISSING');
  });
});
