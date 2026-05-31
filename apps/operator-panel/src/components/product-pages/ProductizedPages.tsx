import type React from 'react';

type ProductPageProps = {
  events?: unknown[];
  driftEvents?: unknown[];
  runItems?: unknown[];
  pendingApprovals?: unknown[];
  claims?: unknown;
  operationOutputs?: Record<string, unknown>;
  operatorId?: string;
  profile?: string;
};

type Metric = {
  label: string;
  value: string | number;
  detail: string;
};

type TableRow = {
  id: string;
  title: string;
  meta: string;
  status: string;
};

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}

function readString(source: Record<string, unknown>, key: string, fallback = ''): string {
  const value = source[key];
  return typeof value === 'string' ? value : fallback;
}

function readArray(source: Record<string, unknown>, key: string): unknown[] {
  const value = source[key];
  return Array.isArray(value) ? value : [];
}

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
  metrics: Metric[];
  rows: TableRow[];
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

export function LogsPage({ events = [], runItems = [] }: ProductPageProps) {
  const rows = (events.length > 0 ? events : runItems).slice(0, 6).map((item, index) => {
    const record = asRecord(item);
    return {
      id: `${index}-${readString(record, 'event', readString(record, 'job_id', 'log'))}`,
      title: readString(record, 'event', readString(record, 'job_id', 'Runtime event')),
      meta: readString(record, 'timestamp', readString(record, 'created_at', 'recent')),
      status: readString(record, 'status', readString(record, 'type', 'observed')),
    };
  });
  return (
    <ProductPageShell
      kicker="Event timeline"
      title="Logs"
      lead="Filter runtime events, drift signals, and run-linked logs without leaving the console."
      metrics={[
        { label: 'Observed events', value: events.length, detail: 'loaded in preview window' },
        { label: 'Linked runs', value: runItems.length, detail: 'available for drilldown' },
        { label: 'Export state', value: 'ready', detail: 'local export remains operator initiated' },
      ]}
      rows={rows.length > 0 ? rows : [{ id: 'empty-log', title: 'No events loaded', meta: 'refresh context', status: 'empty' }]}
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

export function ReportsPage({ operationOutputs = {}, claims }: ProductPageProps) {
  const claimRows = readArray(asRecord(claims), 'claims');
  return (
    <ProductPageShell
      kicker="Readiness evidence"
      title="Reports"
      lead="Review generated readiness, evidence, support, security, and metrics reports from one place."
      metrics={[
        { label: 'GA readiness', value: readString(asRecord(operationOutputs.qualification), 'go_no_go', 'conditional'), detail: 'latest known state' },
        { label: 'Security baseline', value: readString(asRecord(operationOutputs.security), 'overall_status', 'not run'), detail: 'operator triggered' },
        { label: 'Claim records', value: claimRows.length, detail: 'claim guard matrix' },
      ]}
      rows={[
        { id: 'ga-readiness', title: 'GA readiness report', meta: 'artifacts/ga_readiness_report.json', status: 'signed when generated' },
        { id: 'security-baseline', title: 'Security baseline', meta: 'enterprise profile', status: 'local evidence' },
        { id: 'support-bundle', title: 'Support bundle manifest', meta: 'redacted export', status: 'operator initiated' },
      ]}
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

export function AlertsPage({ driftEvents = [], pendingApprovals = [], claims }: ProductPageProps) {
  const blockedClaims = readArray(asRecord(claims), 'claims').filter(
    (claim) => readString(asRecord(claim), 'status') === 'blocked',
  );
  const rows: TableRow[] = [
    ...driftEvents.slice(0, 4).map((item, index) => {
      const record = asRecord(item);
      return {
        id: `drift-${index}`,
        title: readString(record, 'event', 'Runtime drift signal'),
        meta: readString(record, 'timestamp', 'runtime'),
        status: 'warning',
      };
    }),
    ...blockedClaims.slice(0, 4).map((item) => {
      const record = asRecord(item);
      return {
        id: readString(record, 'claim_id', 'claim'),
        title: readString(record, 'claim_id', 'Blocked claim'),
        meta: readArray(record, 'blocking_reasons').join(', ') || 'claim guard',
        status: 'blocked',
      };
    }),
  ];
  return (
    <ProductPageShell
      kicker="Alert inbox"
      title="Alerts"
      lead="Prioritize blocked claims, stale approvals, runtime drift, and unsafe execution attempts."
      metrics={[
        { label: 'Open alerts', value: rows.length, detail: 'derived from runtime signals' },
        { label: 'Pending approvals', value: pendingApprovals.length, detail: 'operator queue' },
        { label: 'Blocked claims', value: blockedClaims.length, detail: 'claim guard' },
      ]}
      rows={rows.length > 0 ? rows : [{ id: 'no-alerts', title: 'No open alert records', meta: 'runtime healthy', status: 'clear' }]}
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

export function PlansPage({ profile = 'balanced' }: ProductPageProps) {
  return (
    <ProductPageShell
      kicker="Plan templates"
      title="Plans"
      lead="Prepare governed task specs, validate safety posture, and submit through the task workspace."
      metrics={[
        { label: 'Templates', value: 3, detail: 'pilot, evidence, remediation' },
        { label: 'Default profile', value: profile, detail: 'used for validation' },
        { label: 'Submission', value: 'gated', detail: 'approval policy applies' },
      ]}
      rows={[
        { id: 'restricted-pilot', title: 'Restricted pilot team', meta: 'examples/team/restricted_pilot.yaml', status: 'validated' },
        { id: 'governed-ops', title: 'Governed operations agent', meta: 'examples/control_plane/agent_governed_ops.yaml', status: 'policy simulation ready' },
        { id: 'evidence-review', title: 'Evidence review run', meta: 'export, verify, summarize', status: 'draft' },
      ]}
    >
      <article className="page-card">
        <h3>Safe next step</h3>
        <p className="supporting">Open Görevler, keep approval checks enabled, and submit the selected plan as a governed run.</p>
      </article>
    </ProductPageShell>
  );
}

export function UsersPage({ operatorId = '', profile = 'balanced' }: ProductPageProps) {
  return (
    <ProductPageShell
      kicker="Identity"
      title="Users"
      lead="Inspect operator identity, verified assertions, and last-known permission context."
      metrics={[
        { label: 'Active operator', value: operatorId || 'not set', detail: 'required for mutations' },
        { label: 'Profile', value: profile, detail: 'settings source' },
        { label: 'Identity mode', value: operatorId ? 'local operator' : 'missing', detail: 'fail-closed mutations' },
      ]}
      rows={[
        { id: 'active-operator', title: operatorId || 'Set operator id', meta: 'Settings > Operator ID', status: operatorId ? 'active' : 'required' },
        { id: 'enterprise-admin', title: 'enterprise-admin', meta: 'fixture assertion', status: 'available in enterprise gate' },
      ]}
    >
      <article className="page-card">
        <h3>Permission checks</h3>
        <p className="supporting">Use Yürütmeler &gt; Identity to run live permission checks against the selected profile.</p>
      </article>
    </ProductPageShell>
  );
}

export function RolesPage({ profile = 'balanced' }: ProductPageProps) {
  return (
    <ProductPageShell
      kicker="RBAC"
      title="Roles"
      lead="Review built-in role responsibilities and the permissions required for guarded operations."
      metrics={[
        { label: 'Built-in roles', value: 3, detail: 'operator, admin, security' },
        { label: 'Profile', value: profile, detail: 'role checks inherit profile' },
        { label: 'Mutation gate', value: 'operator id', detail: 'required before bridge mutations' },
      ]}
      rows={[
        { id: 'operator', title: 'Operator', meta: 'runtime.run, approval.decide', status: 'day-to-day' },
        { id: 'platform-admin', title: 'Platform admin', meta: 'config.write, backup.create', status: 'privileged' },
        { id: 'security-admin', title: 'Security admin', meta: 'keys.rotate, audit.export', status: 'sensitive' },
      ]}
    >
      <article className="page-card">
        <h3>Fail-closed rule</h3>
        <p className="supporting">Unsafe actions remain disabled until identity and permission checks are satisfied.</p>
      </article>
    </ProductPageShell>
  );
}

export function PolicyPacksPage({ claims }: ProductPageProps) {
  const claimRows = readArray(asRecord(claims), 'claims');
  return (
    <ProductPageShell
      kicker="Admin policy"
      title="Policy Packs"
      lead="Manage policy pack visibility separately from the simulation workspace."
      metrics={[
        { label: 'Active packs', value: 2, detail: 'restricted + enterprise' },
        { label: 'Claim rules', value: claimRows.length, detail: 'claim matrix entries' },
        { label: 'Simulation', value: 'linked', detail: 'use Policy for dry-run decisions' },
      ]}
      rows={[
        { id: 'restricted', title: 'restricted-pilot', meta: 'approval-heavy default', status: 'active' },
        { id: 'enterprise', title: 'enterprise-control-plane', meta: 'identity + signing required', status: 'conditional' },
        { id: 'computer-use', title: 'computer-use-live', meta: 'qualification-gated', status: 'blocked' },
      ]}
    >
      <article className="page-card">
        <h3>Assignment rules</h3>
        <p className="supporting">Policy pack edits are represented here as read-only until signed admin workflows are wired.</p>
      </article>
    </ProductPageShell>
  );
}
