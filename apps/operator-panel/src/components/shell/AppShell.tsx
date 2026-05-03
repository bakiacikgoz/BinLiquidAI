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
  operatorId,
  previewMode,
  operatorWarning,
  contractWarning,
  onNavigate,
  onToggleNav,
  onCloseNav,
  onRefresh,
}: {
  children: ReactNode;
  rightRail: ReactNode;
  toasts: ToastItem[];
  activeView: ShellViewKey;
  mobileNavOpen: boolean;
  operatorId: string;
  previewMode: boolean;
  operatorWarning: string;
  contractWarning: string;
  onNavigate: (view: ShellViewKey) => void;
  onToggleNav: () => void;
  onCloseNav: () => void;
  onRefresh: () => void;
}) {
  return (
    <div className={mobileNavOpen ? 'shell shell-nav-open premium-shell' : 'shell premium-shell'}>
      <button
        type="button"
        className={mobileNavOpen ? 'sidebar-backdrop sidebar-backdrop-open' : 'sidebar-backdrop'}
        aria-label="Navigasyonu kapat"
        onClick={onCloseNav}
      />
      <Sidebar
        activeView={activeView}
        open={mobileNavOpen}
        operatorId={operatorId}
        onNavigate={onNavigate}
        onClose={onCloseNav}
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
      {rightRail}
      <ToastHost toasts={toasts} />
    </div>
  );
}
