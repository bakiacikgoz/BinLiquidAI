import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';

import { renderOperatorPanel } from '../../test/render';
import { Sidebar } from './Sidebar';

describe('Sidebar interactions', () => {
  it('navigates and closes the mobile sidebar after selecting a view', async () => {
    const onNavigate = vi.fn();
    const onClose = vi.fn();
    const { user } = renderOperatorPanel(
      <Sidebar
        activeView="workspace"
        open
        collapsed={false}
        operatorId="qa-operator"
        pendingApprovalCount={2}
        warningCount={1}
        onClose={onClose}
        onToggleCollapse={vi.fn()}
        onNavigate={onNavigate}
      />,
    );

    await user.click(screen.getByRole('button', { name: /Görevler/i }));

    expect(onNavigate).toHaveBeenCalledWith('tasks');
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
