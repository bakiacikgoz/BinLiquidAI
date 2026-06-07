import type React from 'react';

import {
  buildAlertsPageModel,
  buildLogsPageModel,
  buildPlansPageModel,
  buildPolicyPacksPageModel,
  buildReportsPageModel,
  buildRolesPageModel,
  buildUsersPageModel,
  type ProductPageMetric,
  type ProductPageRow,
} from '../../control-plane/mappers/governance';
import type { ControlPlaneSnapshot } from '../../control-plane/types';
import type { UiLocale } from '../../i18n';
import { CodeToken, ReasonChip, StatusBadge } from '../primitives/Token';

type ProductPageProps = {
  events?: unknown[];
  driftEvents?: unknown[];
  runItems?: unknown[];
  pendingApprovals?: unknown[];
  claims?: unknown;
  operationOutputs?: Record<string, unknown>;
  operatorId?: string;
  profile?: string;
  snapshot?: ControlPlaneSnapshot | null;
  locale?: UiLocale;
};

type ProductPageCopy = {
  kicker: string;
  title: string;
  lead: string;
  primaryQueue: string;
  sideCardTitle?: string;
};

const productPageCopy: Record<UiLocale, Record<string, ProductPageCopy>> = {
  en: {
    logs: {
      kicker: 'Event timeline',
      title: 'Logs',
      lead: 'Filter runtime events, drift signals, and run-linked logs without leaving the console.',
      primaryQueue: 'Primary queue',
      sideCardTitle: 'Filters',
    },
    reports: {
      kicker: 'Readiness evidence',
      title: 'Reports',
      lead: 'Review generated readiness, evidence, support, security, and metrics reports from one place.',
      primaryQueue: 'Primary queue',
      sideCardTitle: 'Pilot launch report',
    },
    alerts: {
      kicker: 'Alert inbox',
      title: 'Alerts',
      lead: 'Prioritize blocked claims, stale approvals, runtime drift, and unsafe execution attempts.',
      primaryQueue: 'Primary queue',
      sideCardTitle: 'Lifecycle',
    },
    plans: {
      kicker: 'Plan templates',
      title: 'Plans',
      lead: 'Prepare governed task specs, validate safety posture, and submit through the task workspace.',
      primaryQueue: 'Primary queue',
      sideCardTitle: 'Safe next step',
    },
    users: {
      kicker: 'Identity',
      title: 'Users',
      lead: 'Inspect operator identity, verified assertions, and last-known permission context.',
      primaryQueue: 'Primary queue',
      sideCardTitle: 'Admin proposals',
    },
    roles: {
      kicker: 'RBAC',
      title: 'Roles',
      lead: 'Review built-in role responsibilities and the permissions required for guarded operations.',
      primaryQueue: 'Primary queue',
      sideCardTitle: 'Admin proposals',
    },
    policyPacks: {
      kicker: 'Admin policy',
      title: 'Policy Packs',
      lead: 'Manage policy pack visibility separately from the simulation workspace.',
      primaryQueue: 'Primary queue',
      sideCardTitle: 'Lifecycle proposals',
    },
  },
  tr: {
    logs: {
      kicker: 'Olay zaman akışı',
      title: 'Loglar',
      lead: 'Runtime olaylarını, drift sinyallerini ve çalıştırma loglarını konsoldan ayrılmadan filtreleyin.',
      primaryQueue: 'Ana kuyruk',
      sideCardTitle: 'Filtreler',
    },
    reports: {
      kicker: 'Hazırlık kanıtları',
      title: 'Raporlar',
      lead: 'Hazırlık, kanıt, destek, güvenlik ve metrik raporlarını tek yerden inceleyin.',
      primaryQueue: 'Ana kuyruk',
      sideCardTitle: 'Pilot başlatma raporu',
    },
    alerts: {
      kicker: 'Uyarı gelen kutusu',
      title: 'Uyarılar',
      lead: 'Bloke claimleri, bekleyen onayları, runtime driftini ve güvenli olmayan yürütme girişimlerini önceliklendirin.',
      primaryQueue: 'Ana kuyruk',
      sideCardTitle: 'Yaşam döngüsü',
    },
    plans: {
      kicker: 'Plan şablonları',
      title: 'Planlamalar',
      lead: 'Yönetişimli görev tanımlarını hazırlayın, güvenlik duruşunu doğrulayın ve görev alanından gönderin.',
      primaryQueue: 'Ana kuyruk',
      sideCardTitle: 'Güvenli sonraki adım',
    },
    users: {
      kicker: 'Kimlik',
      title: 'Kullanıcılar',
      lead: 'Operatör kimliğini, doğrulanmış beyanları ve son bilinen yetki bağlamını inceleyin.',
      primaryQueue: 'Ana kuyruk',
      sideCardTitle: 'Yönetici önerileri',
    },
    roles: {
      kicker: 'RBAC',
      title: 'Roller',
      lead: 'Yerleşik rol sorumluluklarını ve korumalı operasyonlar için gereken yetkileri inceleyin.',
      primaryQueue: 'Ana kuyruk',
      sideCardTitle: 'Yönetici önerileri',
    },
    policyPacks: {
      kicker: 'Yönetim politikası',
      title: 'Politikalar',
      lead: 'Policy pack görünürlüğünü simülasyon çalışma alanından ayrı yönetin.',
      primaryQueue: 'Ana kuyruk',
      sideCardTitle: 'Yaşam döngüsü önerileri',
    },
  },
};

function ProductPageShell({
  kicker,
  title,
  lead,
  metrics,
  rows,
  primaryQueueLabel,
  children,
}: {
  kicker: string;
  title: string;
  lead: string;
  metrics: ProductPageMetric[];
  rows: ProductPageRow[];
  primaryQueueLabel: string;
  children?: React.ReactNode;
}) {
  return (
    <section className="workspace" data-testid="page-primary-region">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">{kicker}</p>
          <h2>{title}</h2>
          <p className="workspace-lead">{lead}</p>
        </div>
      </div>
      <div className="metric-grid">
        {metrics.map((metric) => (
          <article className="metric-card" key={metric.label}>
            <h3>{metric.label}</h3>
            <p className="metric">{metric.value}</p>
            <small>{metric.detail}</small>
          </article>
        ))}
      </div>
      <div className="section-grid two-up">
        <article className="page-card">
          <h3>{primaryQueueLabel}</h3>
          <div className="run-list">
            {rows.map((row) => (
              <ProductQueueRow key={row.id} row={row} />
            ))}
          </div>
        </article>
        {children}
      </div>
    </section>
  );
}

function ProductQueueRow({ row }: { row: ProductPageRow }) {
  return (
    <article className="run-list-item product-row">
      <div className="run-list-main">
        <strong>{row.title}</strong>
        <div className="run-list-meta">{splitMeta(row.meta).map((part) => renderMetaPart(part))}</div>
      </div>
      <StatusBadge tone={statusTone(row.status)} title={row.status}>
        {row.status}
      </StatusBadge>
    </article>
  );
}

function splitMeta(meta: string): string[] {
  return meta
    .split(/\s+\/\s+|,\s+/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function renderMetaPart(part: string) {
  if (isReasonCode(part)) {
    return (
      <ReasonChip key={part} title={part}>
        {part}
      </ReasonChip>
    );
  }
  if (isTechnicalValue(part)) {
    return (
      <CodeToken key={part} title={part}>
        {part}
      </CodeToken>
    );
  }
  return <span key={part}>{part}</span>;
}

function isReasonCode(value: string): boolean {
  return /^[A-Z][A-Z0-9_]{6,}$/.test(value) || value.startsWith('DATA_SOURCE_') || value.endsWith('_DISABLED');
}

function isTechnicalValue(value: string): boolean {
  return /[/.@:_-]/.test(value) || value.length > 28;
}

function statusTone(status: string): 'neutral' | 'success' | 'warning' | 'error' | 'info' | 'muted' {
  const normalized = status.toLowerCase();
  if (/(ready|active|enabled|clear|passed|healthy|validated|available)/.test(normalized)) {
    return 'success';
  }
  if (/(blocked|failed|deny|error|missing|required)/.test(normalized)) {
    return 'error';
  }
  if (/(conditional|warning|pending|approval|draft|stale)/.test(normalized)) {
    return 'warning';
  }
  if (/(empty|unknown|not run)/.test(normalized)) {
    return 'muted';
  }
  return 'info';
}

export function LogsPage({ events = [], runItems = [], snapshot, locale = 'en' }: ProductPageProps) {
  const copy = productPageCopy[locale].logs;
  const model = buildLogsPageModel(snapshot, { events, runItems });
  return (
    <ProductPageShell
      kicker={copy.kicker}
      title={copy.title}
      lead={copy.lead}
      metrics={model.metrics}
      rows={model.rows}
      primaryQueueLabel={copy.primaryQueue}
    >
      <article className="page-card">
        <h3>{copy.sideCardTitle}</h3>
        <div className="metric-list">
          <div className="metric-row">
            <span>Severity</span>
            <strong>all</strong>
          </div>
          <div className="metric-row">
            <span>Source</span>
            <strong>runtime + control plane</strong>
          </div>
          <div className="metric-row">
            <span>Retention</span>
            <strong>local artifact root</strong>
          </div>
        </div>
      </article>
    </ProductPageShell>
  );
}

export function ReportsPage({ operationOutputs = {}, claims, snapshot, locale = 'en' }: ProductPageProps) {
  const copy = productPageCopy[locale].reports;
  const model = buildReportsPageModel(snapshot, { operationOutputs, claims }, locale);
  return (
    <ProductPageShell
      kicker={copy.kicker}
      title={copy.title}
      lead={copy.lead}
      metrics={model.metrics}
      rows={model.rows}
      primaryQueueLabel={copy.primaryQueue}
    >
      <article className="page-card">
        <h3>{copy.sideCardTitle}</h3>
        <div className="metric-list">
          <div className="metric-row">
            <span>Status</span>
            <strong>{snapshot?.pilotLaunch.status ?? 'unknown'}</strong>
          </div>
          <div className="metric-row">
            <span>Report</span>
            <strong>{snapshot?.pilotLaunch.artifactRoot ?? 'missing'}</strong>
          </div>
          <div className="metric-row">
            <span>Metrics</span>
            <strong>{snapshot?.pilotLaunch.pilotMetrics.status ?? 'unknown'}</strong>
          </div>
        </div>
      </article>
    </ProductPageShell>
  );
}

export function AlertsPage({ driftEvents = [], pendingApprovals = [], claims, snapshot, locale = 'en' }: ProductPageProps) {
  const copy = productPageCopy[locale].alerts;
  const model = buildAlertsPageModel(snapshot, { driftEvents, pendingApprovals, claims }, locale);
  return (
    <ProductPageShell
      kicker={copy.kicker}
      title={copy.title}
      lead={copy.lead}
      metrics={model.metrics}
      rows={model.rows}
      primaryQueueLabel={copy.primaryQueue}
    >
      <article className="page-card">
        <h3>{copy.sideCardTitle}</h3>
        <div className="metric-list">
          <div className="metric-row">
            <span>Acknowledge</span>
            <strong>requires operator identity</strong>
          </div>
          <div className="metric-row">
            <span>Resolve</span>
            <strong>evidence or replay proof</strong>
          </div>
        </div>
      </article>
    </ProductPageShell>
  );
}

export function PlansPage({ profile = 'balanced', snapshot, locale = 'en' }: ProductPageProps) {
  const copy = productPageCopy[locale].plans;
  const model = buildPlansPageModel(snapshot, profile, locale);
  return (
    <ProductPageShell
      kicker={copy.kicker}
      title={copy.title}
      lead={copy.lead}
      metrics={model.metrics}
      rows={model.rows}
      primaryQueueLabel={copy.primaryQueue}
    >
      <article className="page-card">
        <h3>{copy.sideCardTitle}</h3>
        <p className="supporting">Open Görevler, keep approval checks enabled, and submit the selected plan as a governed run.</p>
      </article>
    </ProductPageShell>
  );
}

export function UsersPage({ operatorId = '', profile = 'balanced', snapshot, locale = 'en' }: ProductPageProps) {
  const copy = productPageCopy[locale].users;
  const model = buildUsersPageModel(snapshot, operatorId, profile);
  return (
    <ProductPageShell
      kicker={copy.kicker}
      title={copy.title}
      lead={copy.lead}
      metrics={model.metrics}
      rows={model.rows}
      primaryQueueLabel={copy.primaryQueue}
    >
      <article className="page-card">
        <h3>{copy.sideCardTitle}</h3>
        <div className="metric-list">
          <div className="metric-row">
            <span>Pending</span>
            <strong>{snapshot?.pilotLaunch.adminProposals.filter((item) => item.status !== 'applied').length ?? 0}</strong>
          </div>
          <div className="metric-row">
            <span>Apply gate</span>
            <strong>approval required</strong>
          </div>
        </div>
      </article>
    </ProductPageShell>
  );
}

export function RolesPage({ profile = 'balanced', snapshot, locale = 'en' }: ProductPageProps) {
  const copy = productPageCopy[locale].roles;
  const model = buildRolesPageModel(snapshot, profile);
  return (
    <ProductPageShell
      kicker={copy.kicker}
      title={copy.title}
      lead={copy.lead}
      metrics={model.metrics}
      rows={model.rows}
      primaryQueueLabel={copy.primaryQueue}
    >
      <article className="page-card">
        <h3>{copy.sideCardTitle}</h3>
        <div className="metric-list">
          <div className="metric-row">
            <span>Role proposals</span>
            <strong>{snapshot?.pilotLaunch.adminProposals.filter((item) => item.kind === 'role').length ?? 0}</strong>
          </div>
          <div className="metric-row">
            <span>Audit</span>
            <strong>signed on apply</strong>
          </div>
        </div>
      </article>
    </ProductPageShell>
  );
}

export function PolicyPacksPage({ claims, snapshot, locale = 'en' }: ProductPageProps) {
  const copy = productPageCopy[locale].policyPacks;
  const model = buildPolicyPacksPageModel(snapshot, claims, locale);
  return (
    <ProductPageShell
      kicker={copy.kicker}
      title={copy.title}
      lead={copy.lead}
      metrics={model.metrics}
      rows={model.rows}
      primaryQueueLabel={copy.primaryQueue}
    >
      <article className="page-card">
        <h3>{copy.sideCardTitle}</h3>
        <div className="metric-list">
          <div className="metric-row">
            <span>Policy proposals</span>
            <strong>{snapshot?.pilotLaunch.adminProposals.filter((item) => item.kind === 'policy_pack').length ?? 0}</strong>
          </div>
          <div className="metric-row">
            <span>Rollback</span>
            <strong>plan required</strong>
          </div>
        </div>
      </article>
    </ProductPageShell>
  );
}
