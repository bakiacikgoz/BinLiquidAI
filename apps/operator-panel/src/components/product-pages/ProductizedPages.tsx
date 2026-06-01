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
};

function ProductPageShell({
  kicker,
  title,
  lead,
  metrics,
  rows,
  children,
}: {
  kicker: string;
  title: string;
  lead: string;
  metrics: ProductPageMetric[];
  rows: ProductPageRow[];
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
          <h3>Primary queue</h3>
          <div className="run-list">
            {rows.map((row) => (
              <article className="run-list-item" key={row.id}>
                <strong>{row.title}</strong>
                <span>{row.meta}</span>
                <small>{row.status}</small>
              </article>
            ))}
          </div>
        </article>
        {children}
      </div>
    </section>
  );
}

export function LogsPage({ events = [], runItems = [], snapshot }: ProductPageProps) {
  const model = buildLogsPageModel(snapshot, { events, runItems });
  return (
    <ProductPageShell
      kicker="Event timeline"
      title="Logs"
      lead="Filter runtime events, drift signals, and run-linked logs without leaving the console."
      metrics={model.metrics}
      rows={model.rows}
    >
      <article className="page-card">
        <h3>Filters</h3>
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

export function ReportsPage({ operationOutputs = {}, claims, snapshot }: ProductPageProps) {
  const model = buildReportsPageModel(snapshot, { operationOutputs, claims });
  return (
    <ProductPageShell
      kicker="Readiness evidence"
      title="Reports"
      lead="Review generated readiness, evidence, support, security, and metrics reports from one place."
      metrics={model.metrics}
      rows={model.rows}
    >
      <article className="page-card">
        <h3>Report actions</h3>
        <div className="metric-list">
          <div className="metric-row">
            <span>Generate</span>
            <strong>Operations &gt; Qualification</strong>
          </div>
          <div className="metric-row">
            <span>Verify</span>
            <strong>Evidence center</strong>
          </div>
          <div className="metric-row">
            <span>Share</span>
            <strong>Support bundle</strong>
          </div>
        </div>
      </article>
    </ProductPageShell>
  );
}

export function AlertsPage({ driftEvents = [], pendingApprovals = [], claims, snapshot }: ProductPageProps) {
  const model = buildAlertsPageModel(snapshot, { driftEvents, pendingApprovals, claims });
  return (
    <ProductPageShell
      kicker="Alert inbox"
      title="Alerts"
      lead="Prioritize blocked claims, stale approvals, runtime drift, and unsafe execution attempts."
      metrics={model.metrics}
      rows={model.rows}
    >
      <article className="page-card">
        <h3>Lifecycle</h3>
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

export function PlansPage({ profile = 'balanced', snapshot }: ProductPageProps) {
  const model = buildPlansPageModel(snapshot, profile);
  return (
    <ProductPageShell
      kicker="Plan templates"
      title="Plans"
      lead="Prepare governed task specs, validate safety posture, and submit through the task workspace."
      metrics={model.metrics}
      rows={model.rows}
    >
      <article className="page-card">
        <h3>Safe next step</h3>
        <p className="supporting">Open Görevler, keep approval checks enabled, and submit the selected plan as a governed run.</p>
      </article>
    </ProductPageShell>
  );
}

export function UsersPage({ operatorId = '', profile = 'balanced', snapshot }: ProductPageProps) {
  const model = buildUsersPageModel(snapshot, operatorId, profile);
  return (
    <ProductPageShell
      kicker="Identity"
      title="Users"
      lead="Inspect operator identity, verified assertions, and last-known permission context."
      metrics={model.metrics}
      rows={model.rows}
    >
      <article className="page-card">
        <h3>Permission checks</h3>
        <p className="supporting">Use Yürütmeler &gt; Identity to run live permission checks against the selected profile.</p>
      </article>
    </ProductPageShell>
  );
}

export function RolesPage({ profile = 'balanced', snapshot }: ProductPageProps) {
  const model = buildRolesPageModel(snapshot, profile);
  return (
    <ProductPageShell
      kicker="RBAC"
      title="Roles"
      lead="Review built-in role responsibilities and the permissions required for guarded operations."
      metrics={model.metrics}
      rows={model.rows}
    >
      <article className="page-card">
        <h3>Fail-closed rule</h3>
        <p className="supporting">Unsafe actions remain disabled until identity and permission checks are satisfied.</p>
      </article>
    </ProductPageShell>
  );
}

export function PolicyPacksPage({ claims, snapshot }: ProductPageProps) {
  const model = buildPolicyPacksPageModel(snapshot, claims);
  return (
    <ProductPageShell
      kicker="Admin policy"
      title="Policy Packs"
      lead="Manage policy pack visibility separately from the simulation workspace."
      metrics={model.metrics}
      rows={model.rows}
    >
      <article className="page-card">
        <h3>Assignment rules</h3>
        <p className="supporting">Policy pack edits are represented here as read-only until signed admin workflows are wired.</p>
      </article>
    </ProductPageShell>
  );
}
