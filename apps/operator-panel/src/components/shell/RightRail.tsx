import { Badge } from '../primitives/Badge';
import { Button } from '../primitives/Button';
import { Icon } from '../primitives/Icon';
import { ProgressBar } from '../primitives/ProgressBar';
import { StatusDot } from '../primitives/StatusDot';
import { NotificationStack, type NotificationItem } from '../notifications/NotificationStack';

export type PendingApprovalSummary = {
  id: string;
  title: string;
  subtitle: string;
  time: string;
};

export function RightRail({
  notifications,
  selectedRunId,
  sessionId,
  mode,
  profile,
  startedAt,
  duration,
  coreMode,
  contractVersion,
  health,
  pendingApprovals,
  onDismissNotification,
  onRefreshContext,
  onResume,
  onOpenTerminal,
  onExport,
  onCancel,
  onViewDetails,
  onViewApprovals,
}: {
  notifications: NotificationItem[];
  selectedRunId: string;
  sessionId: string;
  mode: string;
  profile: string;
  startedAt: string;
  duration: string;
  coreMode: string;
  contractVersion: string;
  health: string;
  pendingApprovals: PendingApprovalSummary[];
  onDismissNotification: (id: string) => void;
  onRefreshContext: () => void;
  onResume: () => void;
  onOpenTerminal: () => void;
  onExport: () => void;
  onCancel: () => void;
  onViewDetails: () => void;
  onViewApprovals: () => void;
}) {
  return (
    <aside className="context-rail premium-right-rail">
      <NotificationStack items={notifications} onDismiss={onDismissNotification} />

      <section className="rail-card system-health-card">
        <div className="rail-card-head">
          <span>SİSTEM SAĞLIĞI</span>
          <Badge tone={health.toLowerCase() === 'healthy' ? 'success' : 'warning'}>
            <StatusDot tone="success" /> {health}
          </Badge>
        </div>
        <div className="rail-metrics">
          <div>
            <span>Çekirdek Modu</span>
            <strong>
              {coreMode} <StatusDot tone="success" />
            </strong>
          </div>
          <div>
            <span>Sözleşme Sürümü</span>
            <strong>{contractVersion}</strong>
          </div>
          <div>
            <span>Bellek Kullanımı</span>
            <strong>42%</strong>
            <ProgressBar value={42} />
          </div>
          <div>
            <span>CPU Kullanımı</span>
            <strong>18%</strong>
            <ProgressBar value={18} />
          </div>
          <div>
            <span>Disk Kullanımı</span>
            <strong>27%</strong>
            <ProgressBar value={27} />
          </div>
          <div>
            <span>Ağ Durumu</span>
            <strong className="rail-healthy">Healthy <StatusDot tone="success" /></strong>
          </div>
        </div>
      </section>

      <section className="rail-card selected-run-card">
        <span className="rail-title">SEÇİLİ ÇALIŞTIRMA</span>
        <dl>
          <div>
            <dt>Çalıştırma ID</dt>
            <dd>{selectedRunId || '-'}</dd>
          </div>
          <div>
            <dt>Oturum</dt>
            <dd>{sessionId}</dd>
          </div>
          <div>
            <dt>Mod</dt>
            <dd>{mode}</dd>
          </div>
          <div>
            <dt>Profil</dt>
            <dd>{profile}</dd>
          </div>
          <div>
            <dt>Başlangıç</dt>
            <dd>{startedAt}</dd>
          </div>
          <div>
            <dt>Süre</dt>
            <dd>{duration}</dd>
          </div>
        </dl>
        <Button variant="ghost" onClick={onViewDetails}>
          Ayrıntıları Görüntüle
        </Button>
      </section>

      <section className="rail-card pending-approvals-card">
        <div className="rail-card-head">
          <span>BEKLEYEN ONAYLAR</span>
          <Badge tone="warning">{pendingApprovals.length}</Badge>
        </div>
        <div className="pending-approval-list">
          {pendingApprovals.map((approval) => (
            <button type="button" key={approval.id} onClick={onViewApprovals}>
              <StatusDot tone="warning" />
              <span>
                <strong>{approval.title}</strong>
                <em>{approval.subtitle}</em>
              </span>
              <time>{approval.time}</time>
            </button>
          ))}
        </div>
        <Button variant="ghost" onClick={onViewApprovals}>
          Tüm Onayları Görüntüle
        </Button>
      </section>

      <section className="rail-card quick-actions-card">
        <span className="rail-title">HIZLI İŞLEMLER</span>
        <Button icon={<Icon name="refresh" />} variant="ghost" onClick={onRefreshContext}>
          Bağlamı Yenile
        </Button>
        <Button icon={<Icon name="play" />} variant="ghost" onClick={onResume}>
          Çalıştırmayı Devam Ettir
        </Button>
        <Button icon={<Icon name="terminal" />} variant="ghost" onClick={onOpenTerminal}>
          Terminal Aç
        </Button>
        <Button icon={<Icon name="download" />} variant="ghost" onClick={onExport}>
          Logları Dışa Aktar
        </Button>
        <Button icon={<Icon name="reject" />} variant="danger" onClick={onCancel}>
          Çalıştırmayı İptal Et
        </Button>
      </section>
    </aside>
  );
}
