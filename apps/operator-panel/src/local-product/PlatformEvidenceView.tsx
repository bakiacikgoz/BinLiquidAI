import { mapPlatformEvidenceReconciliation } from './platformEvidenceMappers';

export function PlatformEvidenceView({ report }: { report: unknown }) {
  const vm = mapPlatformEvidenceReconciliation(report);
  return (
    <section className="workspace" data-testid="platform-evidence-view">
      <div className="workspace-header">
        <div>
          <p className="eyebrow">Local Product</p>
          <h2>Platform Evidence</h2>
        </div>
        <span className={`status-pill ${vm.status === 'pass' ? 'status-pass' : 'status-warn'}`}>
          {vm.status}
        </span>
      </div>
      <div className="section-grid">
        <article className="metric-card">
          <span className="metric-label">Evidenced</span>
          <strong>{vm.evidencedTargets.join(', ') || 'none'}</strong>
        </article>
        <article className="metric-card">
          <span className="metric-label">Not Evidenced</span>
          <strong>{vm.notEvidencedTargets.join(', ') || 'none'}</strong>
        </article>
        <article className="metric-card">
          <span className="metric-label">Blockers</span>
          <strong>{vm.blockers.join(', ') || 'none'}</strong>
        </article>
      </div>
      <div className="table-shell">
        <table>
          <thead>
            <tr>
              <th>Target</th>
              <th>Status</th>
              <th>Reasons</th>
            </tr>
          </thead>
          <tbody>
            {vm.targets.map((target) => (
              <tr key={target.targetId}>
                <td>{target.targetId}</td>
                <td>{target.status}</td>
                <td>{target.reasonCodes.join(', ') || 'none'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
