import { asControlPlaneAgentList, asControlPlaneClaimMatrix } from '../../controlPlaneMappers';
import type {
  CodeIntelligenceSummary,
  DesignPartnerBetaStatus,
  PilotLaunchReadinessStatus,
  PilotLaunchStatusTile,
  PilotOperationsStatus,
} from '../../control-plane/types';
import { DesignPartnerBetaReadinessCard } from './DesignPartnerBetaReadinessCard';

export function ControlPlaneDashboard({
  doctor,
  agents,
  claims,
  pendingApprovals,
  pilotLaunch,
  codeIntelligence,
  pilotOperations,
  designPartnerBeta,
}: {
  doctor: unknown;
  agents: unknown;
  claims: unknown;
  pendingApprovals: number;
  pilotLaunch?: PilotLaunchReadinessStatus | null;
  codeIntelligence?: CodeIntelligenceSummary | null;
  pilotOperations?: PilotOperationsStatus | null;
  designPartnerBeta?: DesignPartnerBetaStatus | null;
}) {
  const doctorRecord = asRecord(doctor);
  const agentList = asControlPlaneAgentList(agents);
  const claimMatrix = asControlPlaneClaimMatrix(claims);
  const claimCounts = countClaims(claimMatrix.claims);

  return (
    <section className="workspace" data-testid="page-primary-region">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">Agent Control Plane</p>
          <h2>Dashboard</h2>
          <p className="workspace-lead">Policy, approvals, evidence and execution boundaries.</p>
        </div>
      </div>
      <DashboardMetricGrid
        doctorRecord={doctorRecord}
        agentCount={agentList.agents.length}
        pendingApprovals={pendingApprovals}
        blockedClaims={claimCounts.blocked}
        pilotLaunch={pilotLaunch}
        designPartnerBeta={designPartnerBeta}
        codeIntelligence={codeIntelligence}
      />
      <div className="section-grid two-up">
        <SafetyPostureCard doctorRecord={doctorRecord} claimCounts={claimCounts} />
        <PilotLaunchCandidateCard pilotLaunch={pilotLaunch} />
        <NextActionsCard pilotLaunch={pilotLaunch} />
        <DesignPartnerBetaReadinessCard
          codeIntelligence={codeIntelligence}
          pilotOperations={pilotOperations}
          designPartnerBeta={designPartnerBeta}
        />
      </div>
    </section>
  );
}

function DashboardMetricGrid({
  doctorRecord,
  agentCount,
  pendingApprovals,
  blockedClaims,
  pilotLaunch,
  designPartnerBeta,
  codeIntelligence,
}: {
  doctorRecord: Record<string, unknown>;
  agentCount: number;
  pendingApprovals: number;
  blockedClaims: number;
  pilotLaunch?: PilotLaunchReadinessStatus | null;
  designPartnerBeta?: DesignPartnerBetaStatus | null;
  codeIntelligence?: CodeIntelligenceSummary | null;
}) {
  const metrics = dashboardMetrics({
    doctorRecord,
    agentCount,
    pendingApprovals,
    blockedClaims,
    pilotLaunch,
    designPartnerBeta,
    codeIntelligence,
  });
  return (
    <div className="metric-grid">
      {metrics.map((metric) => (
        <MetricCard
          key={metric.title}
          title={metric.title}
          value={metric.value}
          detail={metric.detail}
        />
      ))}
    </div>
  );
}

function dashboardMetrics({
  doctorRecord,
  agentCount,
  pendingApprovals,
  blockedClaims,
  pilotLaunch,
  designPartnerBeta,
  codeIntelligence,
}: {
  doctorRecord: Record<string, unknown>;
  agentCount: number;
  pendingApprovals: number;
  blockedClaims: number;
  pilotLaunch?: PilotLaunchReadinessStatus | null;
  designPartnerBeta?: DesignPartnerBetaStatus | null;
  codeIntelligence?: CodeIntelligenceSummary | null;
}) {
  return [
    {
      title: 'System Safety',
      value: String(doctorRecord.status ?? 'unknown'),
      detail: String(doctorRecord.profile ?? '-'),
    },
    { title: 'Agents', value: String(agentCount), detail: 'registered' },
    { title: 'Pending Approvals', value: String(pendingApprovals), detail: 'operator queue' },
    { title: 'Claim Guard', value: String(blockedClaims), detail: 'blocked claims' },
    pilotLaunchMetric(pilotLaunch),
    betaOpsMetric(designPartnerBeta),
    codeIntelligenceMetric(codeIntelligence),
  ];
}

function pilotLaunchMetric(pilotLaunch: PilotLaunchReadinessStatus | null | undefined) {
  return {
    title: 'Pilot Launch',
    value: pilotLaunch?.status ?? 'unknown',
    detail: pilotLaunch?.generatedAtUtc ?? 'no snapshot',
  };
}

function betaOpsMetric(designPartnerBeta: DesignPartnerBetaStatus | null | undefined) {
  return {
    title: 'Beta Ops',
    value: designPartnerBeta?.status ?? 'unknown',
    detail: designPartnerBeta?.headline ?? 'no snapshot',
  };
}

function codeIntelligenceMetric(codeIntelligence: CodeIntelligenceSummary | null | undefined) {
  return {
    title: 'Code Intelligence',
    value: codeIntelligence?.verdict ?? 'missing',
    detail: `${codeIntelligence?.boundaryViolations ?? 0} boundary violations`,
  };
}

function MetricCard({ title, value, detail }: { title: string; value: string; detail: string }) {
  return (
    <article className="metric-card">
      <h3>{title}</h3>
      <p className="metric">{value}</p>
      <small>{detail}</small>
    </article>
  );
}

function SafetyPostureCard({
  doctorRecord,
  claimCounts,
}: {
  doctorRecord: Record<string, unknown>;
  claimCounts: ReturnType<typeof countClaims>;
}) {
  return (
    <article className="page-card">
      <h3>Safety posture</h3>
      <div className="metric-list">
        <MetricRow label="Readiness" value={String(doctorRecord.status ?? 'unknown')} />
        <MetricRow label="Allowed claims" value={String(claimCounts.allowed)} />
        <MetricRow label="Conditional claims" value={String(claimCounts.conditional)} />
        <MetricRow label="Fail-closed execution" value="enabled" />
      </div>
    </article>
  );
}

function PilotLaunchCandidateCard({
  pilotLaunch,
}: {
  pilotLaunch?: PilotLaunchReadinessStatus | null;
}) {
  return (
    <article className="page-card">
      <h3>Pilot Launch Candidate</h3>
      <div className="metric-list">
        <PilotTileRow tile={pilotLaunch?.enterpriseHatA} fallback="Enterprise Hat A" />
        <PilotTileRow tile={pilotLaunch?.installRehearsal} fallback="Install rehearsal" />
        <PilotTileRow tile={pilotLaunch?.securityReview} fallback="Security review" />
        <PilotTileRow tile={pilotLaunch?.claimGuard} fallback="Claim guard" />
      </div>
    </article>
  );
}

function NextActionsCard({ pilotLaunch }: { pilotLaunch?: PilotLaunchReadinessStatus | null }) {
  const actions = pilotLaunch?.nextActions.length ? pilotLaunch.nextActions : defaultNextActions;
  return (
    <article className="page-card">
      <h3>Next actions</h3>
      <div className="run-list">
        {actions.map((action) => (
          <article className="run-list-item" key={`${action.target}-${action.label}`}>
            <strong>{action.label}</strong>
            <span>{action.target}</span>
            <small>{action.severity}</small>
          </article>
        ))}
      </div>
    </article>
  );
}

const defaultNextActions = [
  { label: 'Review pending approvals', target: 'Approvals', severity: 'info' as const },
  { label: 'Verify evidence pack', target: 'Evidence', severity: 'info' as const },
  { label: 'Simulate policy', target: 'Policy', severity: 'info' as const },
];

function PilotTileRow({ tile, fallback }: { tile?: PilotLaunchStatusTile | null; fallback: string }) {
  return (
    <div className="metric-row">
      <span>{tile?.label ?? fallback}</span>
      <strong>{tile?.status ?? 'unknown'}</strong>
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function countClaims(claims: Array<{ status: string }>) {
  return {
    allowed: claims.filter((claim) => claim.status === 'allowed').length,
    blocked: claims.filter((claim) => claim.status === 'blocked').length,
    conditional: claims.filter((claim) => claim.status === 'conditional').length,
  };
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}
