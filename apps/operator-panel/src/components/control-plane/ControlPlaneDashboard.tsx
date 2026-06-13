import { asControlPlaneAgentList, asControlPlaneClaimMatrix } from '../../controlPlaneMappers';
import type {
  CodeIntelligenceSummary,
  DesignPartnerBetaStatus,
  PilotLaunchReadinessStatus,
  PilotLaunchStatusTile,
  PilotOperationsStatus,
  ProviderGovernanceSnapshot,
  ProviderRuntimeSnapshot,
  TargetEvidenceClosureSummary,
} from '../../control-plane/types';
import type { UiLocale } from '../../i18n';
import { TargetEvidenceClosure } from '../../provider-governance/TargetEvidenceClosure';
import { DesignPartnerBetaReadinessCard } from './DesignPartnerBetaReadinessCard';
import { ProviderTrustSurface } from './ProviderTrustSurface';

const copy = {
  en: {
    kicker: 'Agent Control Plane',
    title: 'Dashboard',
    lead: 'Policy, approvals, evidence and execution boundaries.',
    systemSafety: 'System Safety',
    unknown: 'unknown',
    agents: 'Agents',
    registered: 'registered',
    pendingApprovals: 'Pending Approvals',
    operatorQueue: 'operator queue',
    claimGuard: 'Claim Guard',
    blockedClaims: 'blocked claims',
    pilotLaunch: 'Pilot Launch',
    noSnapshot: 'no snapshot',
    betaOps: 'Beta Ops',
    codeIntelligence: 'Code Intelligence',
    missing: 'missing',
    boundaryViolations: 'boundary violations',
    safetyPosture: 'Safety posture',
    readiness: 'Readiness',
    allowedClaims: 'Allowed claims',
    conditionalClaims: 'Conditional claims',
    failClosedExecution: 'Fail-closed execution',
    enabled: 'enabled',
    pilotLaunchCandidate: 'Pilot Launch Candidate',
    installRehearsal: 'Install rehearsal',
    securityReview: 'Security review',
    nextActions: 'Next actions',
  },
  tr: {
    kicker: 'Agent Control Plane',
    title: 'Dashboard',
    lead: 'Policy, onaylar, evidence ve yürütme sınırları.',
    systemSafety: 'Sistem güvenliği',
    unknown: 'bilinmiyor',
    agents: 'Agentlar',
    registered: 'kayıtlı',
    pendingApprovals: 'Bekleyen onaylar',
    operatorQueue: 'operatör kuyruğu',
    claimGuard: 'Claim koruması',
    blockedClaims: 'blokeli claimler',
    pilotLaunch: 'Pilot yayın',
    noSnapshot: 'snapshot yok',
    betaOps: 'Beta operasyonları',
    codeIntelligence: 'Kod zekası',
    missing: 'eksik',
    boundaryViolations: 'sınır ihlali',
    safetyPosture: 'Güvenlik duruşu',
    readiness: 'Hazırlık',
    allowedClaims: 'İzinli claimler',
    conditionalClaims: 'Koşullu claimler',
    failClosedExecution: 'Fail-closed yürütme',
    enabled: 'aktif',
    pilotLaunchCandidate: 'Pilot yayın adayı',
    installRehearsal: 'Kurulum provası',
    securityReview: 'Güvenlik incelemesi',
    nextActions: 'Sonraki aksiyonlar',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function ControlPlaneDashboard({
  doctor,
  agents,
  claims,
  pendingApprovals,
  pilotLaunch,
  codeIntelligence,
  pilotOperations,
  designPartnerBeta,
  providerGovernance,
  providerRuntime,
  targetEvidenceClosure,
  locale = 'en',
}: {
  doctor: unknown;
  agents: unknown;
  claims: unknown;
  pendingApprovals: number;
  pilotLaunch?: PilotLaunchReadinessStatus | null;
  codeIntelligence?: CodeIntelligenceSummary | null;
  pilotOperations?: PilotOperationsStatus | null;
  designPartnerBeta?: DesignPartnerBetaStatus | null;
  providerGovernance?: ProviderGovernanceSnapshot | null;
  providerRuntime?: ProviderRuntimeSnapshot | null;
  targetEvidenceClosure?: TargetEvidenceClosureSummary | null;
  locale?: UiLocale;
}) {
  const text = copy[locale];
  const doctorRecord = asRecord(doctor);
  const agentList = asControlPlaneAgentList(agents);
  const claimMatrix = asControlPlaneClaimMatrix(claims);
  const claimCounts = countClaims(claimMatrix.claims);

  return (
    <section className="workspace" data-testid="page-primary-region">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">{text.kicker}</p>
          <h2>{text.title}</h2>
          <p className="workspace-lead">{text.lead}</p>
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
        text={text}
      />
      <div className="section-grid two-up">
        <SafetyPostureCard doctorRecord={doctorRecord} claimCounts={claimCounts} text={text} />
        <PilotLaunchCandidateCard pilotLaunch={pilotLaunch} text={text} />
        <NextActionsCard pilotLaunch={pilotLaunch} text={text} />
        <ProviderTrustSurface snapshot={providerGovernance} runtime={providerRuntime} locale={locale} />
        <TargetEvidenceClosure closure={targetEvidenceClosure} />
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
  text,
}: {
  doctorRecord: Record<string, unknown>;
  agentCount: number;
  pendingApprovals: number;
  blockedClaims: number;
  pilotLaunch?: PilotLaunchReadinessStatus | null;
  designPartnerBeta?: DesignPartnerBetaStatus | null;
  codeIntelligence?: CodeIntelligenceSummary | null;
  text: (typeof copy)['en'];
}) {
  const metrics = dashboardMetrics({
    doctorRecord,
    agentCount,
    pendingApprovals,
    blockedClaims,
    pilotLaunch,
    designPartnerBeta,
    codeIntelligence,
    text,
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
  text,
}: {
  doctorRecord: Record<string, unknown>;
  agentCount: number;
  pendingApprovals: number;
  blockedClaims: number;
  pilotLaunch?: PilotLaunchReadinessStatus | null;
  designPartnerBeta?: DesignPartnerBetaStatus | null;
  codeIntelligence?: CodeIntelligenceSummary | null;
  text: (typeof copy)['en'];
}) {
  return [
    {
      title: text.systemSafety,
      value: String(doctorRecord.status ?? text.unknown),
      detail: String(doctorRecord.profile ?? '-'),
    },
    { title: text.agents, value: String(agentCount), detail: text.registered },
    { title: text.pendingApprovals, value: String(pendingApprovals), detail: text.operatorQueue },
    { title: text.claimGuard, value: String(blockedClaims), detail: text.blockedClaims },
    pilotLaunchMetric(pilotLaunch, text),
    betaOpsMetric(designPartnerBeta, text),
    codeIntelligenceMetric(codeIntelligence, text),
  ];
}

function pilotLaunchMetric(pilotLaunch: PilotLaunchReadinessStatus | null | undefined, text: (typeof copy)['en']) {
  return {
    title: text.pilotLaunch,
    value: pilotLaunch?.status ?? text.unknown,
    detail: pilotLaunch?.generatedAtUtc ?? text.noSnapshot,
  };
}

function betaOpsMetric(designPartnerBeta: DesignPartnerBetaStatus | null | undefined, text: (typeof copy)['en']) {
  return {
    title: text.betaOps,
    value: designPartnerBeta?.status ?? text.unknown,
    detail: designPartnerBeta?.headline ?? text.noSnapshot,
  };
}

function codeIntelligenceMetric(codeIntelligence: CodeIntelligenceSummary | null | undefined, text: (typeof copy)['en']) {
  return {
    title: text.codeIntelligence,
    value: codeIntelligence?.verdict ?? text.missing,
    detail: `${codeIntelligence?.boundaryViolations ?? 0} ${text.boundaryViolations}`,
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
  text,
}: {
  doctorRecord: Record<string, unknown>;
  claimCounts: ReturnType<typeof countClaims>;
  text: (typeof copy)['en'];
}) {
  return (
    <article className="page-card">
      <h3>{text.safetyPosture}</h3>
      <div className="metric-list">
        <MetricRow label={text.readiness} value={String(doctorRecord.status ?? text.unknown)} />
        <MetricRow label={text.allowedClaims} value={String(claimCounts.allowed)} />
        <MetricRow label={text.conditionalClaims} value={String(claimCounts.conditional)} />
        <MetricRow label={text.failClosedExecution} value={text.enabled} />
      </div>
    </article>
  );
}

function PilotLaunchCandidateCard({
  pilotLaunch,
  text,
}: {
  pilotLaunch?: PilotLaunchReadinessStatus | null;
  text: (typeof copy)['en'];
}) {
  return (
    <article className="page-card">
      <h3>{text.pilotLaunchCandidate}</h3>
      <div className="metric-list">
        <PilotTileRow tile={pilotLaunch?.enterpriseHatA} fallback="Enterprise Hat A" />
        <PilotTileRow tile={pilotLaunch?.installRehearsal} fallback={text.installRehearsal} />
        <PilotTileRow tile={pilotLaunch?.securityReview} fallback={text.securityReview} />
        <PilotTileRow tile={pilotLaunch?.claimGuard} fallback={text.claimGuard} />
      </div>
    </article>
  );
}

function NextActionsCard({ pilotLaunch, text }: { pilotLaunch?: PilotLaunchReadinessStatus | null; text: (typeof copy)['en'] }) {
  const actions = pilotLaunch?.nextActions.length ? pilotLaunch.nextActions : defaultNextActions;
  return (
    <article className="page-card">
      <h3>{text.nextActions}</h3>
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
