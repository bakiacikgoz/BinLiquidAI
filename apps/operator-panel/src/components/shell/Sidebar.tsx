import { Icon, type IconName } from '../primitives/Icon';
import { StatusDot } from '../primitives/StatusDot';
import { routeGroups, type RouteId } from '../../routeRegistry';

export type ShellViewKey = RouteId;

export type SidebarGroup = {
  title: string;
  items: Array<{
    id: string;
    key: ShellViewKey;
    label: string;
    icon: IconName;
    badgeCount?: number;
  }>;
};

export function Sidebar({
  activeView,
  open,
  collapsed,
  operatorId,
  pendingApprovalCount,
  warningCount,
  onClose,
  onToggleCollapse,
  onNavigate,
}: {
  activeView: ShellViewKey;
  open: boolean;
  collapsed: boolean;
  operatorId: string;
  pendingApprovalCount: number;
  warningCount: number;
  onClose: () => void;
  onToggleCollapse: () => void;
  onNavigate: (view: ShellViewKey) => void;
}) {
  const assistantEnabled = import.meta.env.VITE_OPERATOR_PANEL_ASSISTANT !== '0';
  const groups: SidebarGroup[] = routeGroups.map((group) => ({
    title: group.title,
    items: group.routes
      .filter((item) => assistantEnabled || item.routeId !== 'assistant')
      .map((item) => ({
        id: item.id,
        key: item.routeId,
        label: item.label,
        icon: item.icon,
        badgeCount:
          item.badgeKey === 'pendingApprovals'
            ? pendingApprovalCount
            : item.badgeKey === 'warnings'
              ? warningCount
              : undefined,
      })),
  }));

  const sidebarClassName = [
    'sidebar',
    'premium-sidebar',
    open ? 'sidebar-open' : '',
    collapsed ? 'premium-sidebar-collapsed' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <aside className={sidebarClassName}>
      <div className="premium-brand">
        <div className="brand-mark">
          <Icon name="hex" />
        </div>
        <div>
          <h1>AegisOS</h1>
          <p>Agent Control Plane</p>
        </div>
        <button
          type="button"
          aria-label={collapsed ? 'Menüyü genişlet' : 'Menüyü daralt'}
          title={collapsed ? 'Menüyü genişlet' : 'Menüyü daralt'}
          onClick={open ? onClose : onToggleCollapse}
        >
          <Icon name="chevron" />
        </button>
      </div>

      <nav className="premium-nav" aria-label="Ana navigasyon">
        {groups.map((group) => (
          <div className="premium-nav-group" key={group.title}>
            <span>{group.title}</span>
            {group.items.map((item) => {
              const isActive = item.key === activeView;
              const badge = item.badgeCount && item.badgeCount > 0 ? String(item.badgeCount) : '';
              return (
                <button
                  key={item.id}
                  type="button"
                  aria-label={item.label}
                  title={collapsed ? item.label : undefined}
                  className={isActive ? 'premium-nav-item premium-nav-item-active' : 'premium-nav-item'}
                  onClick={() => {
                    onNavigate(item.key);
                    onClose();
                  }}
                >
                  <Icon name={item.icon} />
                  <span>{item.label}</span>
                  {badge ? <em>{badge}</em> : null}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="operator-identity">
        <div className="operator-avatar">OP</div>
        <StatusDot tone="success" />
        <div>
          <strong>{operatorId || 'operator'}</strong>
          <span>Administrator</span>
        </div>
        <Icon name="chevron" />
      </div>
    </aside>
  );
}
