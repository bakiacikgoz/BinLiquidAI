import { mapSourceInstallRcClaim } from './platformEvidenceHarvestMappers';

export function SourceInstallRcClaimView({ claim }: { claim: unknown }) {
  const vm = mapSourceInstallRcClaim(claim);
  return (
    <section className="workspace" data-testid="source-install-rc-claim-view">
      <div className="workspace-header">
        <div>
          <p className="eyebrow">Release Claim</p>
          <h2>Source Install RC</h2>
        </div>
        <span className={`status-pill ${vm.status === 'pass' ? 'status-pass' : 'status-warn'}`}>
          {vm.status}
        </span>
      </div>
      <div className="section-grid">
        <article className="metric-card">
          <span className="metric-label">Claimed</span>
          <strong>{vm.claimedTargets.join(', ') || 'none'}</strong>
        </article>
        <article className="metric-card">
          <span className="metric-label">Not Evidenced</span>
          <strong>{vm.notEvidencedTargets.join(', ') || 'none'}</strong>
        </article>
        <article className="metric-card">
          <span className="metric-label">Blocked</span>
          <strong>{vm.blockedTargets.map((target) => target.reasonCode).join(', ') || 'none'}</strong>
        </article>
      </div>
      <div className="table-shell">
        <table>
          <thead>
            <tr>
              <th>Allowed Claims</th>
            </tr>
          </thead>
          <tbody>
            {(vm.allowedClaims.length ? vm.allowedClaims : ['none']).map((claim) => (
              <tr key={claim}>
                <td>{claim}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

