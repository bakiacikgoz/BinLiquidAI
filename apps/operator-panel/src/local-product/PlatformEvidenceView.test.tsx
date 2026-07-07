import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PlatformEvidenceView } from './PlatformEvidenceView';

describe('PlatformEvidenceView', () => {
  it('shows evidenced and not-evidenced targets', () => {
    render(
      <PlatformEvidenceView
        report={{
          status: 'pass',
          evidencedTargets: ['windows-x64'],
          notEvidencedTargets: ['darwin-arm64', 'linux-x64'],
          targets: {
            'windows-x64': { status: 'evidenced', reasonCodes: [] },
            'darwin-arm64': { status: 'not_evidenced', reasonCodes: ['TARGET_NOT_EVIDENCED'] },
          },
        }}
      />,
    );

    expect(screen.getByText('Platform Evidence')).toBeInTheDocument();
    expect(screen.getAllByText(/windows-x64/)[0]).toBeInTheDocument();
    expect(screen.getAllByText(/TARGET_NOT_EVIDENCED/)[0]).toBeInTheDocument();
  });
});
