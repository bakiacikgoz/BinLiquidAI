import { mapRcHandoff } from './platformEvidenceMappers';

export function RcHandoffView({ manifest }: { manifest: unknown }) {
  const vm = mapRcHandoff(manifest);
  return (
    <section className="workspace" data-testid="rc-handoff-view">
      <div className="workspace-header">
        <div>
          <p className="eyebrow">Release Candidate</p>
          <h2>RC Handoff</h2>
        </div>
        <span className={`status-pill ${vm.status === 'ready' ? 'status-pass' : 'status-warn'}`}>
          {vm.status}
        </span>
      </div>
      <div className="section-grid">
        <article className="metric-card">
          <span className="metric-label">Branch</span>
          <strong>{vm.branch}</strong>
        </article>
        <article className="metric-card">
          <span className="metric-label">Commit</span>
          <strong>{vm.gitCommit.slice(0, 12)}</strong>
        </article>
        <article className="metric-card">
          <span className="metric-label">Blocked Claims</span>
          <strong>{vm.blockedClaims.join(', ') || 'none'}</strong>
        </article>
      </div>
      <div className="table-shell">
        <table>
          <thead>
            <tr>
              <th>Supported Claims</th>
              <th>Next Steps</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{vm.supportedClaims.join(', ') || 'none'}</td>
              <td>{vm.nextSteps.join(' ') || 'none'}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}
