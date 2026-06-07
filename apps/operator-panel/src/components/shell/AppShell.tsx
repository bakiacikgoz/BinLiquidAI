import { useEffect, useRef, useState, type ReactNode } from 'react';

import { NotificationStack, type NotificationItem } from '../notifications/NotificationStack';
import { ToastHost, type ToastItem } from '../notifications/ToastHost';
import { Icon } from '../primitives/Icon';
import { Sidebar, type ShellViewKey } from './Sidebar';
import { TopControls } from './TopControls';
import type { ThemeMode } from '../../settings';
import type { UiLocale } from '../../i18n';

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
  notificationItems = [],
  themeMode = 'system',
  locale = 'en',
  onNavigate,
  onToggleNav,
  onToggleSidebar,
  onCloseNav,
  onRefresh,
  onDismissNotification,
  onThemeChange,
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
  notificationItems?: NotificationItem[];
  themeMode?: ThemeMode;
  locale?: UiLocale;
  onNavigate: (view: ShellViewKey) => void;
  onToggleNav: () => void;
  onToggleSidebar: () => void;
  onCloseNav: () => void;
  onRefresh: () => void;
  onDismissNotification?: (id: string) => void;
  onThemeChange: (theme: ThemeMode) => void;
}) {
  const mainPanelRef = useRef<HTMLElement | null>(null);
  const [mobileContextOpen, setMobileContextOpen] = useState(false);
  const [mobileNotificationsOpen, setMobileNotificationsOpen] = useState(false);
  const shellClassName = [
    'shell',
    'premium-shell',
    activeView === 'assistant' ? 'shell-assistant-mode' : '',
    mobileNavOpen ? 'shell-nav-open' : '',
    mobileContextOpen ? 'shell-context-open' : '',
    mobileNotificationsOpen ? 'shell-notifications-open' : '',
    sidebarCollapsed ? 'shell-sidebar-collapsed' : '',
  ]
    .filter(Boolean)
    .join(' ');

  useEffect(() => {
    const panel = mainPanelRef.current;
    setMobileContextOpen(false);
    setMobileNotificationsOpen(false);
    if (!panel) {
      return;
    }
    if (typeof panel.scrollTo === 'function') {
      panel.scrollTo({ top: 0, left: 0 });
      return;
    }
    panel.scrollTop = 0;
    panel.scrollLeft = 0;
  }, [activeView]);

  useEffect(() => {
    if (mobileNavOpen) {
      setMobileContextOpen(false);
      setMobileNotificationsOpen(false);
    }
  }, [mobileNavOpen]);

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
        themeMode={themeMode}
        locale={locale}
        onNavigate={onNavigate}
        onClose={onCloseNav}
        onToggleCollapse={onToggleSidebar}
        onThemeChange={onThemeChange}
      />
      <main className="main-panel premium-main-panel" ref={mainPanelRef}>
        <TopControls
          previewMode={previewMode}
          operatorWarning={operatorWarning}
          contractWarning={contractWarning}
          themeMode={themeMode}
          contextRailAvailable={Boolean(rightRail)}
          contextRailOpen={mobileContextOpen}
          notificationCount={notificationItems.length}
          notificationOpen={mobileNotificationsOpen}
          onToggleNav={onToggleNav}
          onToggleContextRail={() => {
            setMobileNotificationsOpen(false);
            setMobileContextOpen((value) => !value);
          }}
          onToggleNotifications={() => {
            setMobileContextOpen(false);
            setMobileNotificationsOpen((value) => !value);
          }}
          onCycleTheme={() => {
            onThemeChange(themeMode === 'system' ? 'light' : themeMode === 'light' ? 'dark' : 'system');
          }}
          onRefresh={onRefresh}
        />
        {children}
      </main>
      {rightRail ? (
        <div
          className={mobileContextOpen ? 'shell-context-drawer shell-context-drawer-open' : 'shell-context-drawer'}
          aria-hidden={!mobileContextOpen}
        >
          <button
            type="button"
            className="shell-context-backdrop"
            aria-label="Bağlam panelini kapat"
            onClick={() => setMobileContextOpen(false)}
          />
          <div className="shell-context-panel" role="complementary" aria-label="Sayfa bağlam paneli">
            <div className="shell-context-panel-head">
              <span>Bağlam Paneli</span>
              <button type="button" aria-label="Bağlam panelini kapat" onClick={() => setMobileContextOpen(false)}>
                <Icon name="close" />
              </button>
            </div>
            {rightRail}
          </div>
        </div>
      ) : null}
      <div
        className={
          mobileNotificationsOpen
            ? 'shell-notification-drawer shell-notification-drawer-open'
            : 'shell-notification-drawer'
        }
        aria-hidden={!mobileNotificationsOpen}
      >
        <button
          type="button"
          className="shell-notification-backdrop"
          aria-label="Bildirimleri kapat"
          onClick={() => setMobileNotificationsOpen(false)}
        />
        <div className="shell-notification-panel" role="dialog" aria-label="Bildirimler">
          <div className="shell-notification-panel-head">
            <span>Bildirimler</span>
            <button type="button" aria-label="Bildirimleri kapat" onClick={() => setMobileNotificationsOpen(false)}>
              <Icon name="close" />
            </button>
          </div>
          {notificationItems.length > 0 ? (
            <NotificationStack items={notificationItems} onDismiss={onDismissNotification ?? (() => undefined)} />
          ) : (
            <p className="notification-empty">Yeni bildirim yok</p>
          )}
        </div>
      </div>
      <ToastHost toasts={toasts} />
    </div>
  );
}
