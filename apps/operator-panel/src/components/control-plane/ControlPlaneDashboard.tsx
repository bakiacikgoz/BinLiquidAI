import { asControlPlaneAgentList, asControlPlaneClaimMatrix } from '../../controlPlaneMappers';

export function ControlPlaneDashboard({
  doctor,
  agents,
  claims,
  pendingApprovals,
}: {
  doctor: unknown;
  agents: unknown;
  claims: unknown;
  pendingApprovals: number;
}) {
  const doctorRecord = asRecord(doctor);
  const agentList = asControlPlaneAgentList(agents);
  const claimMatrix = asControlPlaneClaimMatrix(claims);
  const blockedClaims = claimMatrix.claims.filter((claim) => claim.status === 'blocked').length;

  return (
    <section className="workspace">
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
      </div>
    </section>
  );
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}
