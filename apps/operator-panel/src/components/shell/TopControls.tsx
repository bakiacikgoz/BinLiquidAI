import { StatusDot } from '../primitives/StatusDot';

export function TopControls({
  previewMode,
  operatorWarning,
  contractWarning,
  onToggleNav,
  onRefresh,
}: {
  previewMode: boolean;
  operatorWarning: string;
  contractWarning: string;
  onToggleNav: () => void;
  onRefresh: () => void;
}) {
  return (
    <header className="workspace-topbar premium-topbar">
      <button type="button" className="nav-toggle-btn" onClick={onToggleNav}>
        Menü
      </button>
      <div className="premium-topbar-status">
        {previewMode ? <span className="pill pill-preview">Preview</span> : null}
        <span className="pill">
          <StatusDot tone="success" /> CANLI
        </span>
        {operatorWarning ? <span className="warning-inline">{operatorWarning}</span> : null}
        {contractWarning ? <span className="warning-inline">{contractWarning}</span> : null}
      </div>
      <button type="button" className="ghost-btn" onClick={onRefresh}>
        Yenile
      </button>
    </header>
  );
}
