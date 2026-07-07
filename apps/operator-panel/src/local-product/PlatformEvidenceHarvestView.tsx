import { mapPlatformEvidenceHarvest } from './platformEvidenceHarvestMappers';

export function PlatformEvidenceHarvestView({ report }: { report: unknown }) {
  const vm = mapPlatformEvidenceHarvest(report);
  return (
    <section className="workspace" data-testid="platform-evidence-harvest-view">
      <div className="workspace-header">
        <div>
          <p className="eyebrow">Remote Evidence</p>
          <h2>Harvest</h2>
        </div>
        <span className={`status-pill ${vm.status === 'pass' ? 'status-pass' : 'status-warn'}`}>
          {vm.status}
        </span>
      </div>
      <div className="section-grid">
        <article className="metric-card">
          <span className="metric-label">Artifacts</span>
          <strong>{vm.artifactsDiscovered} discovered</strong>
        </article>
        <article className="metric-card">
          <span className="metric-label">Imported</span>
          <strong>{vm.artifactsImported}</strong>
        </article>
        <article className="metric-card">
          <span className="metric-label">Head</span>
          <strong>{vm.headSha.slice(0, 12)}</strong>
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
              <tr key={`${target.target}-${target.status}`}>
                <td>{target.target}</td>
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

