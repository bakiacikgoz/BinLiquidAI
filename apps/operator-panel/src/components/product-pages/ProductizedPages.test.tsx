import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderOperatorPanel } from '../../test/render';
import { LogsPage } from './ProductizedPages';

describe('ProductizedPages', () => {
  it('renders product pages with operator decision hierarchy', () => {
    renderOperatorPanel(
      <LogsPage
        events={[{ event: 'Runtime drift signal', timestamp: '2026-03-08T09:10:00Z', type: 'warning' }]}
        runItems={[]}
        locale="en"
      />,
    );

    expect(screen.getByRole('heading', { name: 'Logs' })).toBeInTheDocument();
    expect(screen.getByText('Current state')).toBeInTheDocument();
    expect(screen.getByText('Why it matters')).toBeInTheDocument();
    expect(screen.getByText('Next action')).toBeInTheDocument();
    expect(screen.getByText('Primary queue')).toBeInTheDocument();
    expect(screen.getByText('Filters')).toBeInTheDocument();
    expect(screen.getAllByText('Runtime drift signal')).toHaveLength(2);
  });
});
