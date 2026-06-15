import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { MainlineRcFreezeView } from './MainlineRcFreezeView';

describe('MainlineRcFreezeView', () => {
  it('renders conditional freeze evidence without raw payloads', () => {
    render(
      <MainlineRcFreezeView
        snapshot={{
          schemaVersion: 'control-plane.mainline-rc-freeze-snapshot/v1',
          status: 'conditional',
          freezeId: 'freeze-local',
          manifestPath: 'artifacts/mainline-rc-freeze/manifest.json',
          stackStatus: 'ready',
          mergeRehearsalStatus: 'pass',
          gateEvidenceStatus: 'conditional',
          artifactScanStatus: 'pass',
          evidenceMode: 'hash_only',
          rawPersistence: false,
          blockers: [],
          warnings: ['REMOTE_CI_NOT_ATTACHED'],
          lastGeneratedAtUtc: '2026-06-15T00:00:00Z',
        }}
      />,
    );

    const view = screen.getByTestId('mainline-rc-freeze');
    expect(view).toHaveTextContent('freeze-local');
    expect(view).toHaveTextContent('stack_ready');
    expect(view).toHaveTextContent('merge_pass');
    expect(view).toHaveTextContent('hash_only');
    expect(view).toHaveTextContent('REMOTE_CI_NOT_ATTACHED');
    expect(view).not.toHaveTextContent('BEGIN RAW');
    expect(view).not.toHaveTextContent('rawPayload');
  });

  it('renders fail-closed missing fallback', () => {
    render(<MainlineRcFreezeView snapshot={null} />);

    const view = screen.getByTestId('mainline-rc-freeze');
    expect(view).toHaveTextContent('not generated');
    expect(view).toHaveTextContent('MAINLINE_RC_FREEZE_MISSING');
    expect(view).toHaveTextContent('raw persistence false');
  });
});
