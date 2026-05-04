import { Icon, type IconName } from '../primitives/Icon';
import { StatusDot } from '../primitives/StatusDot';

export type ShellViewKey = 'workspace' | 'tasks' | 'approvals' | 'runs' | 'system' | 'operations' | 'settings';

export type SidebarGroup = {
  title: string;
  items: Array<{
    id: string;
    key: ShellViewKey;
    label: string;
    icon: IconName;
    activeWhen?: ShellViewKey[];
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
  const groups: SidebarGroup[] = [
    {
      title: 'ÇALIŞMA ALANI',
      items: [
        { id: 'mission-control', key: 'workspace', label: 'Mission Control', icon: 'target' },
        { id: 'runs', key: 'runs', label: 'Çalıştırmalar', icon: 'terminal' },
        { id: 'tasks', key: 'tasks', label: 'Görevler', icon: 'list' },
        { id: 'approvals', key: 'approvals', label: 'Onaylar', icon: 'check', badgeCount: pendingApprovalCount },
        { id: 'executions', key: 'operations', label: 'Yürütmeler', icon: 'clipboard' },
      ],
    },
    {
      title: 'SİSTEM',
      items: [
        { id: 'system-health', key: 'system', label: 'Sistem Sağlığı', icon: 'layers' },
        { id: 'resources', key: 'system', label: 'Kaynaklar', icon: 'box', activeWhen: [] },
        { id: 'connections', key: 'system', label: 'Bağlantılar', icon: 'gauge', activeWhen: [] },
        { id: 'settings', key: 'settings', label: 'Ayarlar', icon: 'settings' },
      ],
    },
    {
      title: 'OPERASYONLAR',
      items: [
        { id: 'logs', key: 'runs', label: 'Loglar', icon: 'logs', activeWhen: [] },
        { id: 'reports', key: 'operations', label: 'Raporlar', icon: 'report', activeWhen: [] },
        { id: 'warnings', key: 'operations', label: 'Uyarılar', icon: 'bell', activeWhen: [], badgeCount: warningCount },
        { id: 'plans', key: 'tasks', label: 'Planlamalar', icon: 'play', activeWhen: [] },
      ],
    },
    {
      title: 'YÖNETİM',
      items: [
        { id: 'users', key: 'operations', label: 'Kullanıcılar', icon: 'users', activeWhen: [] },
        { id: 'roles', key: 'operations', label: 'Roller', icon: 'user', activeWhen: [] },
        { id: 'policies', key: 'operations', label: 'Politikalar', icon: 'policy', activeWhen: [] },
      ],
    },
  ];

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
          <p>Operator Runtime</p>
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
              const activeTargets = item.activeWhen ?? [item.key];
              const isActive = activeTargets.includes(activeView);
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
