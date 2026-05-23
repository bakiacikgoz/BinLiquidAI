import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';

import {
  blockedVisionComputerUseCapabilityFixture,
  legacyComputerUseCapabilityFixture,
} from '../../test/fixtures';
import { renderOperatorPanel } from '../../test/render';
import { ComputerUseOperationsCard } from './ComputerUseOperationsCard';

describe('ComputerUseOperationsCard interactions', () => {
  it('keeps blocked computer-use state visible and fail-closed', () => {
    renderOperatorPanel(
      <ComputerUseOperationsCard
        legacyCapability={legacyComputerUseCapabilityFixture}
        visionCapability={blockedVisionComputerUseCapabilityFixture}
        summary={{ counts: { success: 0, blocked: 1, failed: 0, stopped: 0, active: 0 } }}
        runtimeChoice="vision-first"
        startAllowed={false}
        disabledReason="Computer-use live action disabled: MACOS_COMPUTER_USE_NOT_QUALIFIED"
        blockers={['MACOS_COMPUTER_USE_NOT_QUALIFIED']}
        onRuntimeChoiceChange={vi.fn()}
      />,
    );

    expect(screen.getByText('Live gate blocked')).toBeInTheDocument();
    expect(screen.getAllByText('MACOS_COMPUTER_USE_NOT_QUALIFIED').length).toBeGreaterThan(0);
    expect(screen.getByText(/do not start live automation/i)).toBeInTheDocument();
  });

  it('emits runtime changes without starting automation', async () => {
    const onRuntimeChoiceChange = vi.fn();
    const { user } = renderOperatorPanel(
      <ComputerUseOperationsCard
        legacyCapability={legacyComputerUseCapabilityFixture}
        visionCapability={blockedVisionComputerUseCapabilityFixture}
        summary={{ counts: { success: 0, blocked: 1, failed: 0, stopped: 0, active: 0 } }}
        runtimeChoice="vision-first"
        startAllowed={false}
        disabledReason="Computer-use live action disabled: MACOS_COMPUTER_USE_NOT_QUALIFIED"
        blockers={['MACOS_COMPUTER_USE_NOT_QUALIFIED']}
        onRuntimeChoiceChange={onRuntimeChoiceChange}
      />,
    );

    await user.selectOptions(screen.getByRole('combobox', { name: /computer-use runtime/i }), 'legacy-pilot');

    expect(onRuntimeChoiceChange).toHaveBeenCalledWith('legacy-pilot');
  });
});
