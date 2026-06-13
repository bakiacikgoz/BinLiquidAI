import { StatusDot } from '../primitives/StatusDot';
import { Icon } from '../primitives/Icon';
import type { ThemeMode } from '../../settings';

function themeIcon(theme: ThemeMode): 'sun' | 'moon' | 'monitor' {
  if (theme === 'light') {
    return 'sun';
  }
  if (theme === 'dark') {
    return 'moon';
  }
  return 'monitor';
}

export function TopControls({
  previewMode,
  operatorWarning,
  contractWarning,
  themeMode = 'system',
  contextRailAvailable = false,
  contextRailOpen = false,
  notificationCount = 0,
  notificationOpen = false,
  onToggleNav,
  onToggleContextRail,
  onToggleNotifications,
  onCycleTheme,
  onRefresh,
}: {
  previewMode: boolean;
  operatorWarning: string;
  contractWarning: string;
  themeMode?: ThemeMode;
  contextRailAvailable?: boolean;
  contextRailOpen?: boolean;
  notificationCount?: number;
  notificationOpen?: boolean;
  onToggleNav: () => void;
  onToggleContextRail?: () => void;
  onToggleNotifications?: () => void;
  onCycleTheme: () => void;
  onRefresh: () => void;
}) {
  return (
    <header className="workspace-topbar premium-topbar">
      <button
        type="button"
        className="nav-toggle-btn nav-toggle-icon-btn"
        aria-label="Navigasyonu aç"
        title="Navigasyonu aç"
        onClick={onToggleNav}
      >
        <Icon name="chevron" />
      </button>
      <div className="premium-topbar-status">
        {previewMode ? <span className="pill pill-preview">Preview</span> : null}
        <span className="pill">
          <StatusDot tone="success" /> CANLI
        </span>
        {operatorWarning ? (
          <span
            className="warning-inline topbar-warning-inline"
            role="status"
            aria-label="Identity required"
            title={operatorWarning}
          >
            <Icon name="shield" />
            <span className="topbar-warning-text">{operatorWarning}</span>
          </span>
        ) : null}
        {contractWarning ? (
          <span
            className="warning-inline topbar-warning-inline"
            role="status"
            aria-label={contractWarning}
            title={contractWarning}
          >
            <Icon name="alert" />
            <span className="topbar-warning-text">{contractWarning}</span>
          </span>
        ) : null}
      </div>
      <button
        type="button"
        className="theme-toggle-btn theme-cycle-btn"
        aria-label="Tema değiştir"
        title={`Tema: ${themeMode}`}
        onClick={onCycleTheme}
      >
        <Icon name={themeIcon(themeMode)} />
      </button>
      <button
        type="button"
        className="theme-toggle-btn topbar-notification-toggle"
        aria-label={notificationOpen ? 'Bildirimleri kapat' : 'Bildirimleri aç'}
        aria-expanded={notificationOpen}
        title="Bildirimler"
        onClick={onToggleNotifications}
      >
        <Icon name="bell" />
        {notificationCount > 0 ? <span aria-label={`${notificationCount} bildirim`}>{notificationCount}</span> : null}
      </button>
      {contextRailAvailable ? (
        <button
          type="button"
          className="theme-toggle-btn topbar-context-toggle"
          aria-label={contextRailOpen ? 'Bağlam panelini kapat' : 'Bağlam panelini aç'}
          aria-expanded={contextRailOpen}
          title="Bağlam paneli"
          onClick={onToggleContextRail}
        >
          <Icon name="list" />
        </button>
      ) : null}
      <button type="button" className="ghost-btn" onClick={onRefresh}>
        Yenile
      </button>
    </header>
  );
}
