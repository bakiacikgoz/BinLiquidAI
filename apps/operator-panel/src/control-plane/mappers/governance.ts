import type { ControlPlaneSnapshot } from '../types';

export type ProductPageMetric = {
  label: string;
  value: string | number;
  detail: string;
};

export type ProductPageRow = {
  id: string;
  title: string;
  meta: string;
  status: string;
};

export type ProductPageModel = {
  metrics: ProductPageMetric[];
  rows: ProductPageRow[];
};

type LogsFallback = {
  events: unknown[];
  runItems: unknown[];
};

type ReportsFallback = {
  operationOutputs: Record<string, unknown>;
  claims: unknown;
};

type AlertsFallback = {
  driftEvents: unknown[];
  pendingApprovals: unknown[];
  claims: unknown;
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

function sourceDetail(snapshot?: ControlPlaneSnapshot | null): string {
  return snapshot ? `${snapshot.dataSource.mode} / ${snapshot.dataSource.freshness}` : 'legacy bridge context';
}

export function buildLogsPageModel(snapshot: ControlPlaneSnapshot | null | undefined, fallback: LogsFallback): ProductPageModel {
  if (snapshot) {
    return {
      metrics: [
        { label: 'Observed events', value: snapshot.logs.length, detail: sourceDetail(snapshot) },
        { label: 'Linked runs', value: snapshot.runs.length, detail: 'from snapshot run store' },
        { label: 'Source freshness', value: snapshot.dataSource.freshness, detail: snapshot.generatedAtUtc },
      ],
      rows:
        snapshot.logs.length > 0
          ? snapshot.logs.slice(0, 8).map((item) => ({
              id: item.eventId,
              title: item.message,
              meta: `${item.timestamp} / ${item.source}`,
              status: item.severity,
            }))
          : [{ id: 'empty-log', title: 'No events loaded', meta: sourceDetail(snapshot), status: 'empty' }],
    };
  }

  const rows = (fallback.events.length > 0 ? fallback.events : fallback.runItems).slice(0, 6).map((item, index) => {
    const record = asRecord(item);
    return {
      id: `${index}-${readString(record, 'event', readString(record, 'job_id', 'log'))}`,
      title: readString(record, 'event', readString(record, 'job_id', 'Runtime event')),
      meta: readString(record, 'timestamp', readString(record, 'created_at', 'recent')),
      status: readString(record, 'status', readString(record, 'type', 'observed')),
    };
  });

  return {
    metrics: [
      { label: 'Observed events', value: fallback.events.length, detail: 'loaded in preview window' },
      { label: 'Linked runs', value: fallback.runItems.length, detail: 'available for drilldown' },
      { label: 'Export state', value: 'ready', detail: 'local export remains operator initiated' },
    ],
    rows: rows.length > 0 ? rows : [{ id: 'empty-log', title: 'No events loaded', meta: 'refresh context', status: 'empty' }],
  };
}

export function buildReportsPageModel(
  snapshot: ControlPlaneSnapshot | null | undefined,
  fallback: ReportsFallback,
): ProductPageModel {
  if (snapshot) {
    return {
      metrics: [
        { label: 'Reports', value: snapshot.reports.length, detail: sourceDetail(snapshot) },
        {
          label: 'Ready',
          value: snapshot.reports.filter((item) => item.status === 'ready').length,
          detail: 'generated artifacts',
        },
        { label: 'Evidence packs', value: snapshot.evidencePacks.length, detail: 'included in snapshot' },
      ],
      rows:
        snapshot.reports.length > 0
          ? snapshot.reports.slice(0, 8).map((item) => ({
              id: item.reportId,
              title: item.title,
              meta: item.path || item.blockingReasons.join(', ') || item.kind,
              status: item.status,
            }))
          : [{ id: 'empty-report', title: 'No reports loaded', meta: sourceDetail(snapshot), status: 'missing' }],
    };
  }

  const claimRows = readArray(asRecord(fallback.claims), 'claims');
  return {
    metrics: [
      {
        label: 'GA readiness',
        value: readString(asRecord(fallback.operationOutputs.qualification), 'go_no_go', 'conditional'),
        detail: 'latest known state',
      },
      {
        label: 'Security baseline',
        value: readString(asRecord(fallback.operationOutputs.security), 'overall_status', 'not run'),
        detail: 'operator triggered',
      },
      { label: 'Claim records', value: claimRows.length, detail: 'claim guard matrix' },
    ],
    rows: [
      { id: 'ga-readiness', title: 'GA readiness report', meta: 'artifacts/ga_readiness_report.json', status: 'signed when generated' },
      { id: 'security-baseline', title: 'Security baseline', meta: 'enterprise profile', status: 'local evidence' },
      { id: 'support-bundle', title: 'Support bundle manifest', meta: 'redacted export', status: 'operator initiated' },
    ],
  };
}

export function buildAlertsPageModel(snapshot: ControlPlaneSnapshot | null | undefined, fallback: AlertsFallback): ProductPageModel {
  if (snapshot) {
    const activeAlerts = snapshot.alerts.filter((item) => item.status === 'active');
    return {
      metrics: [
        { label: 'Open alerts', value: activeAlerts.length, detail: sourceDetail(snapshot) },
        { label: 'Pending approvals', value: snapshot.approvals.filter((item) => item.status === 'pending').length, detail: 'snapshot queue' },
        { label: 'Blocked claims', value: snapshot.dashboard.blockedClaimCount, detail: 'claim guard' },
      ],
      rows:
        snapshot.alerts.length > 0
          ? snapshot.alerts.slice(0, 8).map((item) => ({
              id: item.alertId,
              title: item.title,
              meta: `${item.reasonCode} / ${item.recommendedAction}`,
              status: `${item.severity}:${item.status}`,
            }))
          : [{ id: 'no-alerts', title: 'No open alert records', meta: sourceDetail(snapshot), status: 'clear' }],
    };
  }

  const blockedClaims = readArray(asRecord(fallback.claims), 'claims').filter(
    (claim) => readString(asRecord(claim), 'status') === 'blocked',
  );
  const rows: ProductPageRow[] = [
    ...fallback.driftEvents.slice(0, 4).map((item, index) => {
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

  return {
    metrics: [
      { label: 'Open alerts', value: rows.length, detail: 'derived from runtime signals' },
      { label: 'Pending approvals', value: fallback.pendingApprovals.length, detail: 'operator queue' },
      { label: 'Blocked claims', value: blockedClaims.length, detail: 'claim guard' },
    ],
    rows: rows.length > 0 ? rows : [{ id: 'no-alerts', title: 'No open alert records', meta: 'runtime healthy', status: 'clear' }],
  };
}

export function buildPlansPageModel(snapshot: ControlPlaneSnapshot | null | undefined, profile: string): ProductPageModel {
  if (snapshot) {
    return {
      metrics: [
        { label: 'Quick actions', value: snapshot.quickActions.length, detail: sourceDetail(snapshot) },
        { label: 'Enabled actions', value: snapshot.quickActions.filter((item) => item.enabled).length, detail: 'operator-ready' },
        { label: 'Profile', value: snapshot.system.profile, detail: 'snapshot source' },
      ],
      rows:
        snapshot.quickActions.length > 0
          ? snapshot.quickActions.map((item) => ({
              id: item.actionId,
              title: item.label,
              meta: item.disabledReason || 'ready',
              status: item.enabled ? 'enabled' : 'blocked',
            }))
          : [{ id: 'no-actions', title: 'No quick actions loaded', meta: sourceDetail(snapshot), status: 'empty' }],
    };
  }

  return {
    metrics: [
      { label: 'Templates', value: 3, detail: 'pilot, evidence, remediation' },
      { label: 'Default profile', value: profile, detail: 'used for validation' },
      { label: 'Submission', value: 'gated', detail: 'approval policy applies' },
    ],
    rows: [
      { id: 'restricted-pilot', title: 'Restricted pilot team', meta: 'examples/team/restricted_pilot.yaml', status: 'validated' },
      { id: 'governed-ops', title: 'Governed operations agent', meta: 'examples/control_plane/agent_governed_ops.yaml', status: 'policy simulation ready' },
      { id: 'evidence-review', title: 'Evidence review run', meta: 'export, verify, summarize', status: 'draft' },
    ],
  };
}

export function buildUsersPageModel(
  snapshot: ControlPlaneSnapshot | null | undefined,
  operatorId: string,
  profile: string,
): ProductPageModel {
  if (snapshot) {
    return {
      metrics: [
        { label: 'Known operators', value: snapshot.admin.users.length, detail: snapshot.admin.source },
        { label: 'Roles', value: snapshot.admin.roles.length, detail: 'permission matrix' },
        { label: 'Source', value: snapshot.admin.source, detail: sourceDetail(snapshot) },
      ],
      rows:
        snapshot.admin.users.length > 0
          ? snapshot.admin.users.map((item) => ({
              id: item.userId,
              title: item.subject,
              meta: `${item.roles.join(', ') || 'no roles'} / ${item.permissions.join(', ') || 'no permissions'}`,
              status: item.status,
            }))
          : [{ id: 'no-users', title: 'No operator identities loaded', meta: snapshot.admin.source, status: 'empty' }],
    };
  }

  return {
    metrics: [
      { label: 'Active operator', value: operatorId || 'not set', detail: 'required for mutations' },
      { label: 'Profile', value: profile, detail: 'settings source' },
      { label: 'Identity mode', value: operatorId ? 'local operator' : 'missing', detail: 'fail-closed mutations' },
    ],
    rows: [
      { id: 'active-operator', title: operatorId || 'Set operator id', meta: 'Settings > Operator ID', status: operatorId ? 'active' : 'required' },
      { id: 'enterprise-admin', title: 'enterprise-admin', meta: 'fixture assertion', status: 'available in enterprise gate' },
    ],
  };
}

export function buildRolesPageModel(snapshot: ControlPlaneSnapshot | null | undefined, profile: string): ProductPageModel {
  if (snapshot) {
    const permissionCount = new Set(snapshot.admin.roles.flatMap((item) => item.permissions)).size;
    return {
      metrics: [
        { label: 'Roles', value: snapshot.admin.roles.length, detail: snapshot.admin.source },
        { label: 'Permissions', value: permissionCount, detail: 'unique grants' },
        { label: 'Policy packs', value: snapshot.admin.policyPacks.length, detail: 'governance scope' },
      ],
      rows:
        snapshot.admin.roles.length > 0
          ? snapshot.admin.roles.map((item) => ({
              id: item.roleId,
              title: item.label,
              meta: item.permissions.join(', ') || 'no permissions',
              status: `${item.riskLevel} risk / ${item.assignmentCount} assignments`,
            }))
          : [{ id: 'no-roles', title: 'No role definitions loaded', meta: snapshot.admin.source, status: 'empty' }],
    };
  }

  return {
    metrics: [
      { label: 'Built-in roles', value: 3, detail: 'operator, admin, security' },
      { label: 'Profile', value: profile, detail: 'role checks inherit profile' },
      { label: 'Mutation gate', value: 'operator id', detail: 'required before bridge mutations' },
    ],
    rows: [
      { id: 'operator', title: 'Operator', meta: 'runtime.run, approval.decide', status: 'day-to-day' },
      { id: 'platform-admin', title: 'Platform admin', meta: 'config.write, backup.create', status: 'privileged' },
      { id: 'security-admin', title: 'Security admin', meta: 'keys.rotate, audit.export', status: 'sensitive' },
    ],
  };
}

export function buildPolicyPacksPageModel(snapshot: ControlPlaneSnapshot | null | undefined, claims: unknown): ProductPageModel {
  if (snapshot) {
    const packs = snapshot.policyPacks.length > 0 ? snapshot.policyPacks : snapshot.admin.policyPacks;
    return {
      metrics: [
        { label: 'Policy packs', value: packs.length, detail: sourceDetail(snapshot) },
        { label: 'Active packs', value: packs.filter((item) => item.status === 'active').length, detail: 'runtime policy' },
        { label: 'Rules', value: packs.reduce((total, item) => total + item.ruleCount, 0), detail: 'declared in packs' },
      ],
      rows:
        packs.length > 0
          ? packs.map((item) => ({
              id: item.packId,
              title: item.label,
              meta: `${item.version} / ${item.sourcePath || item.policyHash || 'no source'}`,
              status: item.blockingReasons.length > 0 ? item.blockingReasons.join(', ') : item.status,
            }))
          : [{ id: 'no-policy-packs', title: 'No policy packs loaded', meta: sourceDetail(snapshot), status: 'missing' }],
    };
  }

  const claimRows = readArray(asRecord(claims), 'claims');
  return {
    metrics: [
      { label: 'Active packs', value: 2, detail: 'restricted + enterprise' },
      { label: 'Claim rules', value: claimRows.length, detail: 'claim matrix entries' },
      { label: 'Simulation', value: 'linked', detail: 'use Policy for dry-run decisions' },
    ],
    rows: [
      { id: 'restricted', title: 'restricted-pilot', meta: 'approval-heavy default', status: 'active' },
      { id: 'enterprise', title: 'enterprise-control-plane', meta: 'identity + signing required', status: 'conditional' },
      { id: 'computer-use', title: 'computer-use-live', meta: 'qualification-gated', status: 'blocked' },
    ],
  };
}
