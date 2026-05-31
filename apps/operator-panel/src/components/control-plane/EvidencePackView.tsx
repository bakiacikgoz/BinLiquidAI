export function EvidencePackView({ evidence }: { evidence: unknown }) {
  const record = asRecord(evidence);
  const verification = asRecord(record.verification);
  return (
    <section className="workspace">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">Evidence</p>
          <h2>Evidence Pack</h2>
          <p className="workspace-lead">
            {String(record.pack_id ?? 'Export or select a signed evidence pack to verify integrity.')}
          </p>
        </div>
      </div>
      <div className="metric-grid">
        <article className="metric-card">
          <h3>Hash Chain</h3>
          <p className="metric">{verification.hash_chain_verified === true ? 'pass' : 'pending'}</p>
        </article>
        <article className="metric-card">
          <h3>Signature</h3>
          <p className="metric">{verification.signature_verified === true ? 'verified' : 'pending'}</p>
        </article>
        <article className="metric-card">
          <h3>Replay</h3>
          <p className="metric">{verification.replay_verified === true ? 'verified' : 'pending'}</p>
        </article>
      </div>
      <div className="section-grid two-up">
        <article className="page-card">
          <h3>Verification checklist</h3>
          <div className="metric-list">
            <div className="metric-row">
              <span>Manifest integrity</span>
              <strong>{verification.hash_chain_verified === true ? 'pass' : 'pending'}</strong>
            </div>
            <div className="metric-row">
              <span>Enterprise signature</span>
              <strong>{verification.signature_verified === true ? 'verified' : 'pending'}</strong>
            </div>
            <div className="metric-row">
              <span>Replay proof</span>
              <strong>{verification.replay_verified === true ? 'verified' : 'pending'}</strong>
            </div>
          </div>
        </article>
        <article className="page-card">
          <h3>Missing evidence</h3>
          <div className="run-list">
            <article className="run-list-item">
              <strong>Qualification report</strong>
              <span>Required before promoting the self-hosted control-plane claim from conditional.</span>
              <small>QUALIFICATION_REPORT_MISSING</small>
            </article>
            <article className="run-list-item">
              <strong>Platform live evidence</strong>
              <span>Required before any live computer-use claim can be opened.</span>
              <small>SIGNED_PLATFORM_QUALIFICATION_MISSING</small>
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
