import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PlatformEvidenceHarvestView } from './PlatformEvidenceHarvestView';

describe('PlatformEvidenceHarvestView', () => {
  it('shows harvest status and target rows', () => {
    render(
      <PlatformEvidenceHarvestView
        report={{
          status: 'pass',
          headSha: 'abcdef123456',
          artifactsDiscovered: 1,
          artifactsImported: 1,
          targetResults: [{ target: 'windows-x64', status: 'evidenced', reasonCodes: [] }],
        }}
      />,
    );

    expect(screen.getByText('Harvest')).toBeInTheDocument();
    expect(screen.getByText('windows-x64')).toBeInTheDocument();
  });
});

