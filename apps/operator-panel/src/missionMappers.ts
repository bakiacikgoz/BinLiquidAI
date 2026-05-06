import type { ActivityItem } from './components/mission/LiveAgentActivity';
import type { RuntimeSummaryItem } from './components/mission/RuntimeSummaryCard';
import type { SessionEventItem } from './components/mission/SessionEventsCard';
import type { MissionStageKey } from './components/mission/StageProgress';
import type { NotificationItem } from './components/notifications/NotificationStack';
import type { PendingApprovalSummary, SystemHealthSummary } from './components/shell/RightRail';
import type { WorkspaceSnapshot, WorkspaceStageKey } from './workspace';

type JsonRecord = Record<string, unknown>;

type ClockFormatter = (value: string, fallback: string) => string;

function asRecord(value: unknown): JsonRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as JsonRecord) : {};
}

function readString(source: JsonRecord, key: string, fallback = ''): string {
  const value = source[key];
  return typeof value === 'string' ? value : fallback;
}

function readFirstString(source: JsonRecord, keys: string[], fallback = ''): string {
  for (const key of keys) {
    const value = readString(source, key);
    if (value) {
      return value;
    }
  }
  return fallback;
}

function readFirstNestedString(source: JsonRecord, keys: string[]): string {
  const queue: JsonRecord[] = [source];
  const seen = new Set<JsonRecord>();

  while (queue.length > 0) {
    const record = queue.shift();
    if (!record || seen.has(record)) {
      continue;
    }
    seen.add(record);

    const value = readFirstString(record, keys);
    if (value) {
      return value;
    }

    for (const entry of Object.values(record)) {
      if (typeof entry === 'object' && entry !== null && !Array.isArray(entry)) {
        queue.push(entry as JsonRecord);
      }
    }
  }

  return '';
}

function humanizeCode(value: string): string {
  return value
    .replaceAll('.', ' ')
    .replaceAll('_', ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function shortClock(value: string, formatClock: ClockFormatter): string {
  const formatted = formatClock(value, '-');
  return formatted === '-' ? '-' : formatted.slice(0, 5);
}

function normalizePercent(value: number): number {
  const percent = value >= 0 && value <= 1 ? value * 100 : value;
  return Math.max(0, Math.min(100, Math.round(percent)));
}

function readFirstMetricPercent(source: JsonRecord, keys: string[]): number | null {
  const queue: JsonRecord[] = [source];
  const seen = new Set<JsonRecord>();

  while (queue.length > 0) {
    const record = queue.shift();
    if (!record || seen.has(record)) {
      continue;
    }
    seen.add(record);

    for (const key of keys) {
      const value = record[key];
      if (typeof value === 'number' && Number.isFinite(value)) {
        return normalizePercent(value);
      }
      if (typeof value === 'string' && value.trim()) {
        const parsed = Number(value.replace('%', ''));
        if (Number.isFinite(parsed)) {
          return normalizePercent(parsed);
        }
      }
    }

    for (const value of Object.values(record)) {
      if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        queue.push(value as JsonRecord);
      }
    }
  }

  return null;
}

function normalizeHealth(value: string): SystemHealthSummary['health'] {
  const status = value.toLowerCase();
  if (status === 'ok' || status === 'healthy' || status === 'pass' || status === 'ready') {
    return 'Healthy';
  }
  if (status === 'warn' || status === 'warning' || status === 'degraded') {
    return 'Degraded';
  }
  if (status === 'blocked' || status === 'error' || status === 'failed' || status === 'fail') {
    return 'Blocked';
  }
  return 'Unknown';
}

function riskBadgeTone(riskClass: string | null): RuntimeSummaryItem['badgeTone'] {
  const normalized = (riskClass ?? '').toLowerCase();
  if (normalized === 'low') {
    return 'success';
  }
  if (normalized === 'high' || normalized === 'critical') {
    return 'error';
  }
  if (normalized === 'medium') {
    return 'warning';
  }
  return 'info';
}

function verificationBadgeTone(status: string | null): RuntimeSummaryItem['badgeTone'] {
  const normalized = (status ?? '').toLowerCase();
  if (normalized === 'satisfied' || normalized === 'skipped') {
    return 'success';
  }
  if (normalized === 'failed') {
    return 'error';
  }
  if (normalized === 'inconclusive') {
    return 'warning';
  }
  return 'info';
}

export function mapWorkspaceStageToMissionStage(
  stage: WorkspaceStageKey,
  hasPendingApproval = false,
): MissionStageKey {
  if (hasPendingApproval || stage === 'waiting_approval' || stage === 'blocked') {
    return 'approval';
  }
  if (stage === 'reading_screen') {
    return 'preparing';
  }
  if (stage === 'executing' || stage === 'verifying') {
    return 'running';
  }
  if (stage === 'done') {
    return 'done';
  }
  return 'planning';
}

export function buildActivityItems(snapshot: WorkspaceSnapshot, formatClock: ClockFormatter): ActivityItem[] {
  if (snapshot.timeline.length === 0) {
    return [
      {
        id: 'activity-empty',
        time: '-',
        title: 'Henüz ajan etkinliği yok.',
        body: snapshot.objective || 'Çalıştırma seçildiğinde canlı etkinlik burada görünür.',
        tone: 'neutral',
      },
    ];
  }

  return snapshot.timeline.slice(-5).reverse().map((item) => ({
    id: item.id,
    time: formatClock(item.timestamp, '-'),
    title: item.summary,
    body: item.event,
    tone: item.tone === 'warning' ? 'warning' : item.tone === 'success' ? 'success' : 'info',
  }));
}

export function buildSessionEventItems(snapshot: WorkspaceSnapshot, formatClock: ClockFormatter): SessionEventItem[] {
  if (snapshot.timeline.length === 0) {
    return [
      {
        id: 'session-empty',
        time: '-',
        title: 'Oturum olayı yok',
        body: 'Runtime olayı geldiğinde bu liste güncellenir.',
        tag: 'SİSTEM',
        tone: 'neutral',
      },
    ];
  }

  return snapshot.timeline.slice(-3).reverse().map((item) => ({
    id: item.id,
    time: shortClock(item.timestamp, formatClock),
    title: item.summary,
    body: item.event,
    tag: item.tone === 'success' ? 'BAĞLAM' : item.tone === 'warning' ? 'UYARI' : 'SİSTEM',
    tone: item.tone === 'warning' ? 'warning' : item.tone === 'success' ? 'success' : 'info',
  }));
}

export function buildRuntimeSummaryItems({
  snapshot,
  selectedRunId,
  hasApproval,
  stageLabel,
  systemHealth,
}: {
  snapshot: WorkspaceSnapshot;
  selectedRunId: string;
  hasApproval: boolean;
  stageLabel: string;
  systemHealth: SystemHealthSummary;
}): RuntimeSummaryItem[] {
  const hasResourceMetrics =
    systemHealth.memoryUsagePct !== null || systemHealth.cpuUsagePct !== null || systemHealth.diskUsagePct !== null;
  const resourceTone: RuntimeSummaryItem['tone'] =
    systemHealth.health === 'Blocked' || systemHealth.health === 'Degraded' ? 'warning' : hasResourceMetrics ? 'success' : 'info';
  const resourceText = hasResourceMetrics
    ? `Kaynak metrikleri gerçek ölçümden okunuyor (${systemHealth.health}).`
    : 'Kaynak metrikleri henüz alınmadı.';

  const vision = snapshot.visionRuntime;
  const visionItems: RuntimeSummaryItem[] = vision
    ? [
        {
          id: 'vision-action',
          tone: vision.requiresApproval ? 'warning' : 'info',
          text: `Vision action: ${vision.actionType ?? 'unknown'}${
            vision.targetElementId ? ` on ${vision.targetElementId}` : ''
          }.${vision.rationale ? ` Rationale: ${vision.rationale}` : ''}`,
          badge: vision.riskClass ?? 'risk unknown',
          badgeTone: riskBadgeTone(vision.riskClass),
        },
        {
          id: 'vision-approval',
          tone: vision.requiresApproval ? 'warning' : 'success',
          text: `Approval: ${vision.approvalState ?? (vision.requiresApproval ? 'required' : 'not required')}.${
            vision.policyDecision ? ` Policy: ${vision.policyDecision}.` : ''
          }`,
        },
        {
          id: 'vision-verifier',
          tone:
            vision.verificationStatus === 'failed' || vision.verificationStatus === 'inconclusive'
              ? 'warning'
              : 'success',
          text: `Verifier: ${vision.verificationStatus ?? 'not reported'}${
            vision.verificationReason ? ` (${vision.verificationReason})` : ''
          }.`,
          badge: vision.verificationStatus ?? 'unknown',
          badgeTone: verificationBadgeTone(vision.verificationStatus),
        },
        ...(vision.stopReason
          ? [
              {
                id: 'vision-stop',
                tone: 'warning' as const,
                text: `Stop reason: ${vision.stopReason}.`,
              },
            ]
          : []),
        {
          id: 'vision-privacy',
          tone: vision.rawScreenshotPathIgnored ? 'warning' : 'success',
          text: vision.rawScreenshotPathIgnored
            ? 'Raw screenshot paths are hidden; redacted metadata only.'
            : 'Raw screenshot paths are not present in the operator summary.',
        },
      ]
    : [];

  return [
    {
      id: 'stage',
      tone: 'success',
      text: `Ajan şu anda ${stageLabel.toLocaleLowerCase('tr-TR')} aşamasında.`,
    },
    {
      id: 'context',
      tone: selectedRunId ? 'success' : 'info',
      text: selectedRunId ? 'Çalışma bağlamı doğrulandı ve geçerli.' : 'Çalıştırma seçildiğinde bağlam yüklenecek.',
    },
    {
      id: 'external',
      tone: snapshot.liveSurface ? 'success' : 'warning',
      text: snapshot.liveSurface ? 'Canlı yüzey bağlantısı izleniyor.' : 'Harici izleyici bağlantısı bulunmuyor.',
    },
    {
      id: 'approval',
      tone: hasApproval ? 'warning' : 'success',
      text: hasApproval
        ? 'Hazırlık sonraki adım için operatör onayı bekleniyor.'
        : 'Bekleyen operatör onayı bulunmuyor.',
    },
    ...visionItems,
    {
      id: 'resources',
      tone: resourceTone,
      text: resourceText,
    },
  ];
}

export function buildNotificationItems({
  approvalRows,
  timeline,
  dismissedIds,
  formatClock,
}: {
  approvalRows: JsonRecord[];
  timeline: WorkspaceSnapshot['timeline'];
  dismissedIds: string[];
  formatClock: ClockFormatter;
}): NotificationItem[] {
  const approvalItems: NotificationItem[] = approvalRows.slice(0, 2).map((approval, index) => {
    const approvalId = readString(approval, 'approval_id', `approval-${index}`);
    const createdAt = readFirstString(approval, ['created_at', 'requested_at', 'expires_at']);
    return {
      id: `approval-${approvalId}`,
      kind: 'warning',
      title: 'Onay talebi oluşturuldu',
      subtitle: readFirstString(approval, ['summary', 'target_kind', 'target_ref'], approvalId),
      time: shortClock(createdAt, formatClock),
    };
  });

  const timelineItems: NotificationItem[] = timeline
    .filter((item) => item.tone === 'warning')
    .slice(-1)
    .reverse()
    .map((item) => ({
      id: `timeline-${item.id}`,
      kind: 'warning',
      title: item.summary,
      subtitle: item.event,
      time: shortClock(item.timestamp, formatClock),
    }));

  return [...approvalItems, ...timelineItems].filter((item) => !dismissedIds.includes(item.id));
}

export function buildPendingApprovalSummaries(
  approvalRows: JsonRecord[],
  selectedRunId: string,
): PendingApprovalSummary[] {
  return approvalRows.slice(0, 2).map((approval, index) => {
    const approvalId = readString(approval, 'approval_id', `approval-${index}`);
    return {
      id: approvalId,
      title: readFirstString(approval, ['summary', 'target_kind'], 'Bekleyen Onay'),
      subtitle: readString(approval, 'run_id') || selectedRunId || '-',
      time: readFirstString(approval, ['created_at', 'requested_at', 'expires_at'], '-'),
    };
  });
}

export function buildSystemHealthSummary({
  coreMode,
  handshakeRecord,
  doctor,
  metricsPayload,
}: {
  coreMode: string;
  handshakeRecord: JsonRecord;
  doctor: JsonRecord;
  metricsPayload: unknown;
}): SystemHealthSummary {
  const metrics = asRecord(metricsPayload);
  const statusSource =
    readFirstString(doctor, ['status', 'health']) || readFirstString(metrics, ['status', 'health'], 'unknown');

  return {
    coreMode,
    contractVersion: readFirstString(handshakeRecord, ['contractVersion', 'contract_version'], '-'),
    health: normalizeHealth(statusSource),
    memoryUsagePct: readFirstMetricPercent(metrics, [
      'memoryUsagePct',
      'memory_usage_pct',
      'memory_pct',
      'memory_percent',
      'mem_pct',
    ]),
    cpuUsagePct: readFirstMetricPercent(metrics, ['cpuUsagePct', 'cpu_usage_pct', 'cpu_pct', 'cpu_percent']),
    diskUsagePct: readFirstMetricPercent(metrics, [
      'diskUsagePct',
      'disk_usage_pct',
      'disk_pct',
      'disk_percent',
      'storage_pct',
    ]),
    networkStatus:
      readFirstNestedString(metrics, ['networkStatus', 'network_status', 'network']) ||
      readFirstString(asRecord(metrics.network), ['status', 'health']) ||
      readFirstString(asRecord(asRecord(metrics.system).network), ['status', 'health']) ||
      null,
  };
}

export { humanizeCode };
