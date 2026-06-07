import { screen, within } from '@testing-library/react';
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
        onThemeChange={vi.fn()}
      >
        <h1>Mission Control</h1>
      </AppShell>,
    );

    await user.click(screen.getByRole('button', { name: 'Navigasyonu kapat' }));

    expect(onCloseNav).toHaveBeenCalledTimes(1);
  });

  it('opens and closes the page context rail drawer', async () => {
    const { user } = renderOperatorPanel(
      <AppShell
        activeView="workspace"
        mobileNavOpen={false}
        sidebarCollapsed={false}
        operatorId="qa-operator"
        previewMode
        operatorWarning=""
        contractWarning=""
        pendingApprovalCount={0}
        warningCount={0}
        toasts={[]}
        rightRail={<aside>Context rail content</aside>}
        onNavigate={vi.fn()}
        onToggleNav={vi.fn()}
        onToggleSidebar={vi.fn()}
        onCloseNav={vi.fn()}
        onRefresh={vi.fn()}
        onThemeChange={vi.fn()}
      >
        <h1>Mission Control</h1>
      </AppShell>,
    );

    await user.click(screen.getByRole('button', { name: 'Bağlam panelini aç' }));

    const panel = screen.getByRole('complementary', { name: 'Sayfa bağlam paneli' });
    expect(panel).toHaveTextContent('Context rail content');

    await user.click(within(panel).getByRole('button', { name: 'Bağlam panelini kapat' }));

    expect(screen.getByRole('button', { name: 'Bağlam panelini aç' })).toBeInTheDocument();
  });

  it('opens system notifications separately from the context rail', async () => {
    const onDismissNotification = vi.fn();
    const { user } = renderOperatorPanel(
      <AppShell
        activeView="workspace"
        mobileNavOpen={false}
        sidebarCollapsed={false}
        operatorId="qa-operator"
        previewMode
        operatorWarning=""
        contractWarning=""
        pendingApprovalCount={0}
        warningCount={0}
        notificationItems={[
          {
            id: 'operator-id-required',
            kind: 'warning',
            title: 'Operatör kimliği gerekli',
            subtitle: 'Devam etmek için operator id girin',
            time: '-',
          },
        ]}
        toasts={[]}
        rightRail={<aside>Context rail content</aside>}
        onNavigate={vi.fn()}
        onToggleNav={vi.fn()}
        onToggleSidebar={vi.fn()}
        onCloseNav={vi.fn()}
        onRefresh={vi.fn()}
        onDismissNotification={onDismissNotification}
        onThemeChange={vi.fn()}
      >
        <h1>Mission Control</h1>
      </AppShell>,
    );

    await user.click(screen.getByRole('button', { name: 'Bildirimleri aç' }));

    const notificationsDialog = screen.getByRole('dialog', { name: 'Bildirimler' });
    expect(notificationsDialog).toHaveTextContent('Operatör kimliği gerekli');
    expect(screen.queryByRole('complementary', { name: 'Sayfa bağlam paneli' })).not.toBeInTheDocument();

    await user.click(within(notificationsDialog).getByRole('button', { name: 'Bildirimi kapat' }));

    expect(onDismissNotification).toHaveBeenCalledWith('operator-id-required');
  });
});
