import { asControlPlaneAgentList, asControlPlaneClaimMatrix } from '../../controlPlaneMappers';
import type { PilotLaunchReadinessStatus, PilotLaunchStatusTile } from '../../control-plane/types';

export function ControlPlaneDashboard({
  doctor,
  agents,
  claims,
  pendingApprovals,
  pilotLaunch,
}: {
  doctor: unknown;
  agents: unknown;
  claims: unknown;
  pendingApprovals: number;
  pilotLaunch?: PilotLaunchReadinessStatus | null;
}) {
  const doctorRecord = asRecord(doctor);
  const agentList = asControlPlaneAgentList(agents);
  const claimMatrix = asControlPlaneClaimMatrix(claims);
  const blockedClaims = claimMatrix.claims.filter((claim) => claim.status === 'blocked').length;
  const conditionalClaims = claimMatrix.claims.filter((claim) => claim.status === 'conditional').length;
  const allowedClaims = claimMatrix.claims.filter((claim) => claim.status === 'allowed').length;

  return (
    <section className="workspace" data-testid="page-primary-region">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">Agent Control Plane</p>
          <h2>Dashboard</h2>
          <p className="workspace-lead">Policy, approvals, evidence and execution boundaries.</p>
        </div>
      </div>
      <div className="metric-grid">
        <article className="metric-card">
          <h3>System Safety</h3>
          <p className="metric">{String(doctorRecord.status ?? 'unknown')}</p>
          <small>{String(doctorRecord.profile ?? '-')}</small>
        </article>
        <article className="metric-card">
          <h3>Agents</h3>
          <p className="metric">{agentList.agents.length}</p>
          <small>registered</small>
        </article>
        <article className="metric-card">
          <h3>Pending Approvals</h3>
          <p className="metric">{pendingApprovals}</p>
          <small>operator queue</small>
        </article>
        <article className="metric-card">
          <h3>Claim Guard</h3>
          <p className="metric">{blockedClaims}</p>
          <small>blocked claims</small>
        </article>
        <article className="metric-card">
          <h3>Pilot Launch</h3>
          <p className="metric">{pilotLaunch?.status ?? 'unknown'}</p>
          <small>{pilotLaunch?.generatedAtUtc ?? 'no snapshot'}</small>
        </article>
      </div>
      <div className="section-grid two-up">
        <article className="page-card">
          <h3>Safety posture</h3>
          <div className="metric-list">
            <div className="metric-row">
              <span>Readiness</span>
              <strong>{String(doctorRecord.status ?? 'unknown')}</strong>
            </div>
            <div className="metric-row">
              <span>Allowed claims</span>
              <strong>{allowedClaims}</strong>
            </div>
            <div className="metric-row">
              <span>Conditional claims</span>
              <strong>{conditionalClaims}</strong>
            </div>
            <div className="metric-row">
              <span>Fail-closed execution</span>
              <strong>enabled</strong>
            </div>
          </div>
        </article>
        <article className="page-card">
          <h3>Pilot Launch Candidate</h3>
          <div className="metric-list">
            <PilotTileRow tile={pilotLaunch?.enterpriseHatA} fallback="Enterprise Hat A" />
            <PilotTileRow tile={pilotLaunch?.installRehearsal} fallback="Install rehearsal" />
            <PilotTileRow tile={pilotLaunch?.securityReview} fallback="Security review" />
            <PilotTileRow tile={pilotLaunch?.claimGuard} fallback="Claim guard" />
          </div>
        </article>
        <article className="page-card">
          <h3>Next actions</h3>
          <div className="run-list">
            {(pilotLaunch?.nextActions.length ? pilotLaunch.nextActions : defaultNextActions).map((action) => (
              <article className="run-list-item" key={`${action.target}-${action.label}`}>
                <strong>{action.label}</strong>
                <span>{action.target}</span>
                <small>{action.severity}</small>
              </article>
            ))}
          </div>
        </article>
      </div>
    </section>
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

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}
