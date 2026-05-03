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

export type SystemHealthStatus = 'Healthy' | 'Degraded' | 'Blocked' | 'Unknown';

export type SystemHealthSummary = {
  coreMode: string;
  contractVersion: string;
  health: SystemHealthStatus;
  memoryUsagePct: number | null;
  cpuUsagePct: number | null;
  diskUsagePct: number | null;
  networkStatus: string | null;
};

function healthTone(health: SystemHealthStatus): 'success' | 'warning' | 'error' | 'info' {
  if (health === 'Healthy') {
    return 'success';
  }
  if (health === 'Blocked') {
    return 'error';
  }
  if (health === 'Degraded') {
    return 'warning';
  }
  return 'info';
}

function formatMetric(value: number | null): string {
  return value === null ? 'Ölçüm yok' : `${value}%`;
}

function MetricRow({ label, value }: { label: string; value: number | null }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{formatMetric(value)}</strong>
      {value !== null ? <ProgressBar value={value} /> : null}
    </div>
  );
}

export function RightRail({
  notifications,
  selectedRunId,
  sessionId,
  mode,
  profile,
  startedAt,
  duration,
  systemHealth,
  pendingApprovals,
  resumeDisabled = false,
  resumeDisabledReason = '',
  terminalDisabled = false,
  terminalDisabledReason = '',
  exportDisabled = false,
  exportDisabledReason = '',
  cancelDisabled = false,
  cancelDisabledReason = '',
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
  systemHealth: SystemHealthSummary;
  pendingApprovals: PendingApprovalSummary[];
  resumeDisabled?: boolean;
  resumeDisabledReason?: string;
  terminalDisabled?: boolean;
  terminalDisabledReason?: string;
  exportDisabled?: boolean;
  exportDisabledReason?: string;
  cancelDisabled?: boolean;
  cancelDisabledReason?: string;
  onDismissNotification: (id: string) => void;
  onRefreshContext: () => void;
  onResume: () => void;
  onOpenTerminal: () => void;
  onExport: () => void;
  onCancel: () => void;
  onViewDetails: () => void;
  onViewApprovals: () => void;
}) {
  const healthBadgeTone = healthTone(systemHealth.health);
  const networkTone = systemHealth.networkStatus === null ? 'muted' : healthBadgeTone;

  return (
    <aside className="context-rail premium-right-rail">
      <NotificationStack items={notifications} onDismiss={onDismissNotification} />

      <section className="rail-card system-health-card">
        <div className="rail-card-head">
          <span>SİSTEM SAĞLIĞI</span>
          <Badge tone={healthBadgeTone}>
            <StatusDot tone={healthBadgeTone} /> {systemHealth.health}
          </Badge>
        </div>
        <div className="rail-metrics">
          <div>
            <span>Çekirdek Modu</span>
            <strong>
              {systemHealth.coreMode || '-'} <StatusDot tone={systemHealth.coreMode ? 'success' : 'muted'} />
            </strong>
          </div>
          <div>
            <span>Sözleşme Sürümü</span>
            <strong>{systemHealth.contractVersion}</strong>
          </div>
          <MetricRow label="Bellek Kullanımı" value={systemHealth.memoryUsagePct} />
          <MetricRow label="CPU Kullanımı" value={systemHealth.cpuUsagePct} />
          <MetricRow label="Disk Kullanımı" value={systemHealth.diskUsagePct} />
          <div>
            <span>Ağ Durumu</span>
            <strong className={systemHealth.networkStatus ? 'rail-healthy' : undefined}>
              {systemHealth.networkStatus ?? '-'} <StatusDot tone={networkTone} />
            </strong>
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
          {pendingApprovals.length > 0 ? (
            pendingApprovals.map((approval) => (
              <button type="button" key={approval.id} onClick={onViewApprovals}>
                <StatusDot tone="warning" />
                <span>
                  <strong>{approval.title}</strong>
                  <em>{approval.subtitle}</em>
                </span>
                <time>{approval.time}</time>
              </button>
            ))
          ) : (
            <p className="rail-empty">Bekleyen onay yok</p>
          )}
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
        <Button
          disabled={resumeDisabled}
          icon={<Icon name="play" />}
          title={resumeDisabledReason || undefined}
          variant="ghost"
          onClick={onResume}
        >
          Çalıştırmayı Devam Ettir
        </Button>
        <Button
          disabled={terminalDisabled}
          icon={<Icon name="terminal" />}
          title={terminalDisabledReason || undefined}
          variant="ghost"
          onClick={onOpenTerminal}
        >
          Terminal Aç
        </Button>
        <Button
          disabled={exportDisabled}
          icon={<Icon name="download" />}
          title={exportDisabledReason || undefined}
          variant="ghost"
          onClick={onExport}
        >
          Logları Dışa Aktar
        </Button>
        <Button
          disabled={cancelDisabled}
          icon={<Icon name="reject" />}
          title={cancelDisabledReason || undefined}
          variant="danger"
          onClick={onCancel}
        >
          Çalıştırmayı İptal Et
        </Button>
      </section>
    </aside>
  );
}
