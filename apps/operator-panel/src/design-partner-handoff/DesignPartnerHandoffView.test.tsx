import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DesignPartnerHandoffView } from './DesignPartnerHandoffView';

describe('DesignPartnerHandoffView', () => {
  it('renders ready handoff status without raw payloads', () => {
    render(
      <DesignPartnerHandoffView
        snapshot={{
          schemaVersion: 'control-plane.design-partner-handoff-snapshot/v1',
          status: 'ready',
          handoffPackPath: 'artifacts/design-partner-handoff/manifest.json',
          releaseTrainStatus: 'pass',
          firstRunDrillStatus: 'pass',
          blockers: [],
          warnings: [],
          lastGeneratedAtUtc: '2026-06-14T00:00:00Z',
          claimBoundarySummary: {
            publicDesktop: 'blocked',
            liveComputerUse: 'blocked',
            approvalFreeIrreversibleMutation: 'blocked',
          },
        }}
      />,
    );

    const view = screen.getByTestId('design-partner-handoff');
    expect(view).toHaveTextContent('release_train_pass');
    expect(view).toHaveTextContent('first_run_pass');
    expect(view).toHaveTextContent('publicDesktop');
    expect(view).toHaveTextContent('blocked');
    expect(view).not.toHaveTextContent('BEGIN RAW');
  });

  it('renders missing handoff fallback', () => {
    render(<DesignPartnerHandoffView snapshot={null} />);

    expect(screen.getByTestId('design-partner-handoff')).toHaveTextContent('not generated');
    expect(screen.getByTestId('design-partner-handoff')).toHaveTextContent(
      'DESIGN_PARTNER_HANDOFF_MISSING',
    );
  });
});
