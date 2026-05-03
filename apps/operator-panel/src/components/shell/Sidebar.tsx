import { Icon, type IconName } from '../primitives/Icon';
import { StatusDot } from '../primitives/StatusDot';

export type ShellViewKey = 'workspace' | 'tasks' | 'approvals' | 'runs' | 'system' | 'operations' | 'settings';

export type SidebarGroup = {
  title: string;
  items: Array<{
    key: ShellViewKey;
    label: string;
    icon: IconName;
    badge?: string;
  }>;
};

export function Sidebar({
  activeView,
  open,
  operatorId,
  onClose,
  onNavigate,
}: {
  activeView: ShellViewKey;
  open: boolean;
  operatorId: string;
  onClose: () => void;
  onNavigate: (view: ShellViewKey) => void;
}) {
  const groups: SidebarGroup[] = [
    {
      title: 'ÇALIŞMA ALANI',
      items: [
        { key: 'workspace', label: 'Mission Control', icon: 'target' },
        { key: 'runs', label: 'Çalıştırmalar', icon: 'terminal' },
        { key: 'tasks', label: 'Görevler', icon: 'list' },
        { key: 'approvals', label: 'Onaylar', icon: 'check', badge: '2' },
        { key: 'operations', label: 'Yürütmeler', icon: 'clipboard' },
      ],
    },
    {
      title: 'SİSTEM',
      items: [
        { key: 'system', label: 'Sistem Sağlığı', icon: 'layers' },
        { key: 'system', label: 'Kaynaklar', icon: 'box' },
        { key: 'system', label: 'Bağlantılar', icon: 'gauge' },
        { key: 'settings', label: 'Ayarlar', icon: 'settings' },
      ],
    },
    {
      title: 'OPERASYONLAR',
      items: [
        { key: 'runs', label: 'Loglar', icon: 'logs' },
        { key: 'operations', label: 'Raporlar', icon: 'report' },
        { key: 'operations', label: 'Uyarılar', icon: 'bell', badge: '1' },
        { key: 'tasks', label: 'Planlamalar', icon: 'play' },
      ],
    },
    {
      title: 'YÖNETİM',
      items: [
        { key: 'operations', label: 'Kullanıcılar', icon: 'users' },
        { key: 'operations', label: 'Roller', icon: 'user' },
        { key: 'operations', label: 'Politikalar', icon: 'policy' },
      ],
    },
  ];

  return (
    <aside className={open ? 'sidebar sidebar-open premium-sidebar' : 'sidebar premium-sidebar'}>
      <div className="premium-brand">
        <div className="brand-mark">
          <Icon name="hex" />
        </div>
        <div>
          <h1>AegisOS</h1>
          <p>Operator Runtime</p>
        </div>
        <button type="button" aria-label="Menüyü daralt" onClick={onClose}>
          <Icon name="chevron" />
        </button>
      </div>

      <nav className="premium-nav" aria-label="Ana navigasyon">
        {groups.map((group) => (
          <div className="premium-nav-group" key={group.title}>
            <span>{group.title}</span>
            {group.items.map((item) => (
              <button
                key={`${group.title}-${item.label}`}
                type="button"
                className={activeView === item.key && item.label === 'Mission Control' ? 'premium-nav-item premium-nav-item-active' : 'premium-nav-item'}
                onClick={() => {
                  onNavigate(item.key);
                  onClose();
                }}
              >
                <Icon name={item.icon} />
                <span>{item.label}</span>
                {item.badge ? <em>{item.badge}</em> : null}
              </button>
            ))}
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
