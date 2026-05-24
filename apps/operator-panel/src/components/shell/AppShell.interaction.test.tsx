import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { renderOperatorPanel } from '../../test/render';
import { AppShell } from './AppShell';

describe('AppShell interactions', () => {
  it('closes the mobile navigation backdrop through the required callback', async () => {
    const onCloseNav = vi.fn();
    const { user } = renderOperatorPanel(
      <AppShell
        activeView="workspace"
        mobileNavOpen
        sidebarCollapsed={false}
        operatorId="qa-operator"
        previewMode
        operatorWarning=""
        contractWarning=""
        pendingApprovalCount={0}
        warningCount={0}
        toasts={[]}
        onNavigate={vi.fn()}
        onToggleNav={vi.fn()}
        onToggleSidebar={vi.fn()}
        onCloseNav={onCloseNav}
        onRefresh={vi.fn()}
      >
        <h1>Mission Control</h1>
      </AppShell>,
    );

    await user.click(screen.getByRole('button', { name: 'Navigasyonu kapat' }));

    expect(onCloseNav).toHaveBeenCalledTimes(1);
  });
});
