import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderOperatorPanel } from '../test/render';
import { MemoryAuthorityView } from './MemoryAuthorityView';

describe('MemoryAuthorityView', () => {
  it('renders authority health without raw memory content', () => {
    renderOperatorPanel(
      <MemoryAuthorityView
        authority={{
          status: 'available',
          mode: 'local_authority',
          workspaceCount: 2,
          principalCount: 3,
          activeScopeCount: 4,
          pendingProposalCount: 1,
          pendingConflictCount: 0,
          lastSyncPackStatus: 'pass',
          rawContentExposed: false,
          networkListenerEnabled: false,
          blockingReasons: [],
        }}
      />,
    );

    expect(screen.getByRole('heading', { name: 'Memory Authority' })).toBeInTheDocument();
    expect(screen.getByTestId('memory-authority-counts')).toHaveTextContent('2');
    expect(screen.getByTestId('memory-authority-status')).toHaveTextContent('blocked');
  });
});
