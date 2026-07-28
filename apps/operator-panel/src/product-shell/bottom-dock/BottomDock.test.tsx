import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import { getAssistantFixture } from '../../assistant/assistantFixtures';
import { renderOperatorPanel } from '../../test/render';
import { useProductShellStore } from '../state/productShellStore';
import { BottomDock } from './BottomDock';

describe('BottomDock', () => {
  beforeEach(() => {
    useProductShellStore.setState({ dockHeight: 240 });
  });

  it('renders real governed content for every enabled UI Lab dock tab', async () => {
    const { container, user } = renderOperatorPanel(<BottomDock state={getAssistantFixture('running')} />);

    expect(container.querySelector('.bottom-dock .dock-tabs')).toBeInTheDocument();
    expect(container.querySelector('.activity-view')).toBeInTheDocument();
    expect(screen.getByText(/recorded turn/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Terminal/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Terminal/ })).toHaveAttribute(
      'data-disabled-reason',
      'DOCK_TERMINAL_CAPABILITY_UNAVAILABLE',
    );

    await user.click(screen.getByRole('button', { name: /Ajan Çalışması/ }));
    expect(screen.getByRole('region', { name: 'Governed run work' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Loglar/ }));
    expect(screen.getByRole('region', { name: 'Assistant timeline logs' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Evidence/ }));
    expect(screen.getByRole('region', { name: 'Governed evidence' })).toBeInTheDocument();
  });

  it('persists keyboard dock resizing in the Product Shell preference store', async () => {
    const { user } = renderOperatorPanel(<BottomDock state={getAssistantFixture('welcome')} />);

    const separator = screen.getByRole('separator', { name: 'Dock height' });
    await user.click(separator);
    await user.keyboard('{ArrowUp}');

    expect(separator).toHaveAttribute('aria-valuenow', '250');
  });
});
