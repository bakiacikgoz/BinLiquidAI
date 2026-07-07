import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { RcHandoffView } from './RcHandoffView';

describe('RcHandoffView', () => {
  it('shows rc handoff status and claims', () => {
    render(
      <RcHandoffView
        manifest={{
          status: 'ready',
          branch: 'codex/multi-host',
          gitCommit: 'abcdef1234567890',
          supportedClaims: ['windows-x64 source/local install evidenced'],
          blockedClaims: [],
          operatorNextSteps: ['Collect missing target evidence.'],
        }}
      />,
    );

    expect(screen.getByText('RC Handoff')).toBeInTheDocument();
    expect(screen.getByText('ready')).toBeInTheDocument();
    expect(screen.getByText(/windows-x64/)).toBeInTheDocument();
  });
});
