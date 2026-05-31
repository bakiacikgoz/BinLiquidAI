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
          <h3>Next actions</h3>
          <div className="run-list">
            <article className="run-list-item">
              <strong>Review pending approvals</strong>
              <span>Confirm actor, policy decision, and execution status before mutating.</span>
              <small>Approvals</small>
            </article>
            <article className="run-list-item">
              <strong>Verify evidence pack</strong>
              <span>Check hash chain, signature, replay, and redaction summary.</span>
              <small>Evidence</small>
            </article>
            <article className="run-list-item">
              <strong>Simulate policy</strong>
              <span>Dry-run actions before submitting governed runs.</span>
              <small>Policy</small>
            </article>
          </div>
        </article>
      </div>
    </section>
  );
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}
