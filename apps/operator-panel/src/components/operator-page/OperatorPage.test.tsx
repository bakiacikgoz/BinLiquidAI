import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { renderOperatorPanel } from '../../test/render';
import { OperatorPageShell } from './OperatorPage';
import { operatorToneFromStatus } from './operatorPageUtils';

describe('OperatorPageShell', () => {
  it('renders decision summary, metrics, context, and actions', async () => {
    const onPrimary = vi.fn();
    const { user } = renderOperatorPanel(
      <OperatorPageShell
        kicker="Evidence"
        title="Signed Evidence"
        lead="Verify release evidence before continuing."
        status="ready"
        actions={[
          { label: 'Refresh', onClick: vi.fn() },
          { label: 'Verify latest', onClick: onPrimary, variant: 'primary' },
        ]}
        decisionItems={[
          { label: 'Current state', value: 'ready', detail: 'Manifest is present.' },
          { label: 'Next action', value: 'Verify', detail: 'Run the latest verification.' },
        ]}
        metrics={[{ label: 'Packs', value: 1, detail: 'run_1' }]}
        context={<article>Claim guard context</article>}
      >
        <article>Primary work area</article>
      </OperatorPageShell>,
    );

    expect(screen.getByRole('heading', { name: 'Signed Evidence' })).toBeInTheDocument();
    expect(screen.getByText('Current state')).toBeInTheDocument();
    expect(screen.getByText('Manifest is present.')).toBeInTheDocument();
    expect(screen.getByText('Packs')).toBeInTheDocument();
    expect(screen.getByText('Primary work area')).toBeInTheDocument();
    expect(screen.getByText('Claim guard context')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Verify latest' }));

    expect(onPrimary).toHaveBeenCalledTimes(1);
  });

  it('exposes disabled action reasons', () => {
    renderOperatorPanel(
      <OperatorPageShell
        kicker="Runs"
        title="Runs"
        status="blocked"
        actions={[
          {
            label: 'Export',
            disabled: true,
            title: 'Select a run first.',
            variant: 'primary',
          },
        ]}
      >
        <article>Run list</article>
      </OperatorPageShell>,
    );

    const exportButton = screen.getByRole('button', { name: 'Export' });

    expect(exportButton).toBeDisabled();
    expect(exportButton).toHaveAttribute('data-disabled-reason', 'Select a run first.');
  });
});

describe('operatorToneFromStatus', () => {
  it('maps operational status text to semantic tones', () => {
    expect(operatorToneFromStatus('ready')).toBe('success');
    expect(operatorToneFromStatus('missing manifest')).toBe('error');
    expect(operatorToneFromStatus('pending approval')).toBe('warning');
    expect(operatorToneFromStatus('unknown')).toBe('muted');
  });
});
