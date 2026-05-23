import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';

import { renderOperatorPanel } from '../../test/render';
import { RightRail, type SystemHealthSummary } from './RightRail';

const systemHealth: SystemHealthSummary = {
  coreMode: 'auto',
  contractVersion: '2.0',
  health: 'Healthy',
  memoryUsagePct: null,
  cpuUsagePct: null,
  diskUsagePct: null,
  networkStatus: null,
};

function renderRail(overrides: Partial<Parameters<typeof RightRail>[0]> = {}) {
  return renderOperatorPanel(
    <RightRail
      notifications={[]}
      selectedRunId="run_qa_1"
      sessionId="session_qa"
      mode="auto"
      profile="balanced"
      startedAt="-"
      duration="-"
      systemHealth={systemHealth}
      pendingApprovals={[]}
      onDismissNotification={vi.fn()}
      onRefreshContext={vi.fn()}
      onResume={vi.fn()}
      onOpenTerminal={vi.fn()}
      onExport={vi.fn()}
      onCancel={vi.fn()}
      onViewDetails={vi.fn()}
      onViewApprovals={vi.fn()}
      {...overrides}
    />,
  );
}

describe('RightRail interactions', () => {
  it('calls enabled quick actions', async () => {
    const onRefreshContext = vi.fn();
    const onExport = vi.fn();
    const { user } = renderRail({ onRefreshContext, onExport });

    await user.click(screen.getByRole('button', { name: /Bağlamı Yenile/i }));
    await user.click(screen.getByRole('button', { name: /Logları Dışa Aktar/i }));

    expect(onRefreshContext).toHaveBeenCalledTimes(1);
    expect(onExport).toHaveBeenCalledTimes(1);
  });

  it('keeps disabled quick actions inert and explains why', async () => {
    const onOpenTerminal = vi.fn();
    const { user } = renderRail({
      terminalDisabled: true,
      terminalDisabledReason: 'Terminal unavailable.',
      onOpenTerminal,
    });
    const terminal = screen.getByRole('button', { name: /Terminal Aç/i });

    expect(terminal).toBeDisabled();
    expect(terminal).toHaveAttribute('title', 'Terminal unavailable.');
    await user.click(terminal);
    expect(onOpenTerminal).not.toHaveBeenCalled();
  });
});
