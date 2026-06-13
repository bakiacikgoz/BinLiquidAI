import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { TargetEvidenceClosure } from './TargetEvidenceClosure';
import type { TargetEvidenceClosureSummary } from './targetEvidenceTypes';

describe('TargetEvidenceClosure', () => {
  it('renders hash-only closure status without raw JSON', () => {
    const closure: TargetEvidenceClosureSummary = {
      contractVersion: 'control-plane.target-evidence-closure/v1',
      generatedAtUtc: '2026-06-01T12:00:00Z',
      status: 'conditional',
      sessionId: 'target-evidence-preview',
      mode: 'rehearsal',
      evidenceMode: 'hash_only',
      rawPersistence: false,
      blockingReasons: [],
      warnings: ['TARGET_ENVIRONMENT_REHEARSAL_ONLY'],
      blockedClaims: [
        'public-desktop-installer',
        'live-macos-computer-use',
        'live-windows-computer-use',
        'live-linux-computer-use',
      ],
      attestationStatus: 'present',
    };

    const html = renderToStaticMarkup(<TargetEvidenceClosure closure={closure} />);

    expect(html).toContain('Target Evidence Closure');
    expect(html).toContain('hash_only');
    expect(html).toContain('raw_persistence_off');
    expect(html).toContain('public-desktop-installer');
    expect(html).toContain('Operator Attestation');
    expect(html).not.toContain('{');
  });
});
