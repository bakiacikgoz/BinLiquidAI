import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { SourceInstallRcClaimView } from './SourceInstallRcClaimView';

describe('SourceInstallRcClaimView', () => {
  it('keeps source install claims target-scoped', () => {
    render(
      <SourceInstallRcClaimView
        claim={{
          status: 'pass',
          claimedTargets: ['windows-x64'],
          notEvidencedTargets: ['linux-x64'],
          releaseNotesAllowedClaims: ['windows-x64 source-local-install evidenced'],
        }}
      />,
    );

    expect(screen.getByText('Source Install RC')).toBeInTheDocument();
    expect(screen.getAllByText(/windows-x64/)[0]).toBeInTheDocument();
    expect(screen.getByText('linux-x64')).toBeInTheDocument();
  });
});

