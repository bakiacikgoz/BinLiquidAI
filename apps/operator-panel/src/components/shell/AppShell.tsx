import type { ReactNode } from 'react';

import { ToastHost, type ToastItem } from '../notifications/ToastHost';
import { Sidebar, type ShellViewKey } from './Sidebar';
import { TopControls } from './TopControls';

export function AppShell({
  children,
  rightRail,
  toasts,
  activeView,
  mobileNavOpen,
  sidebarCollapsed,
  operatorId,
  previewMode,
  operatorWarning,
  contractWarning,
  pendingApprovalCount,
  warningCount,
  onNavigate,
  onToggleNav,
  onToggleSidebar,
  onCloseNav,
  onRefresh,
}: {
  children: ReactNode;
  rightRail?: ReactNode;
  toasts: ToastItem[];
  activeView: ShellViewKey;
  mobileNavOpen: boolean;
  sidebarCollapsed: boolean;
  operatorId: string;
  previewMode: boolean;
  operatorWarning: string;
  contractWarning: string;
  pendingApprovalCount: number;
  warningCount: number;
  onNavigate: (view: ShellViewKey) => void;
  onToggleNav: () => void;
  onToggleSidebar: () => void;
  onCloseNav: () => void;
  onRefresh: () => void;
}) {
  const shellClassName = [
    'shell',
    'premium-shell',
    activeView === 'assistant' ? 'shell-assistant-mode' : '',
    mobileNavOpen ? 'shell-nav-open' : '',
    sidebarCollapsed ? 'shell-sidebar-collapsed' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={shellClassName}>
      <button
        type="button"
        className={mobileNavOpen ? 'sidebar-backdrop sidebar-backdrop-open' : 'sidebar-backdrop'}
        aria-label="Navigasyonu kapat"
        onClick={onCloseNav}
      />
      <Sidebar
        activeView={activeView}
        open={mobileNavOpen}
        collapsed={sidebarCollapsed}
        operatorId={operatorId}
        pendingApprovalCount={pendingApprovalCount}
        warningCount={warningCount}
        onNavigate={onNavigate}
        onClose={onCloseNav}
        onToggleCollapse={onToggleSidebar}
      />
      <main className="main-panel premium-main-panel">
        <TopControls
          previewMode={previewMode}
          operatorWarning={operatorWarning}
          contractWarning={contractWarning}
          onToggleNav={onToggleNav}
          onRefresh={onRefresh}
        />
        {children}
      </main>
      {rightRail ?? null}
      <ToastHost toasts={toasts} />
    </div>
  );
}
