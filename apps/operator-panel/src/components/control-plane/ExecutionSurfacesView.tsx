export function ExecutionSurfacesView({ computerUseCapability }: { computerUseCapability: unknown }) {
  const capability = asRecord(computerUseCapability);
  return (
    <section className="workspace">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">Execution Boundaries</p>
          <h2>Execution Surfaces</h2>
          <p className="workspace-lead">Live surfaces stay disabled unless qualification evidence is present.</p>
        </div>
      </div>
      <div className="section-grid two-up">
        <article className="page-card">
          <h3>Core Runtime</h3>
          <p className="metric">ready</p>
        </article>
        <article className="page-card">
          <h3>Team Runtime</h3>
          <p className="metric">pilot / enterprise gated</p>
        </article>
        <article className="page-card">
          <h3>Computer-use</h3>
          <p className="metric">{String(capability.status ?? 'blocked')}</p>
          <small>{String(capability.reasonCode ?? 'COMPUTER_USE_NOT_QUALIFIED')}</small>
          <span
            className="ghost-btn"
            title="Live computer-use is disabled until qualification evidence is present."
            data-disabled-reason="Live computer-use is disabled until qualification evidence is present."
          >
            Start live
          </span>
        </article>
        <article className="page-card">
          <h3>Public desktop installer</h3>
          <p className="metric">blocked</p>
          <small>HAT_B_EVIDENCE_MISSING</small>
        </article>
      </div>
    </section>
  );
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}
