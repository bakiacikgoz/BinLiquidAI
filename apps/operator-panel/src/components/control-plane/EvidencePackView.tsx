export function EvidencePackView({ evidence }: { evidence: unknown }) {
  const record = asRecord(evidence);
  const verification = asRecord(record.verification);
  return (
    <section className="workspace">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">Evidence</p>
          <h2>Evidence Pack</h2>
          <p className="workspace-lead">{String(record.pack_id ?? 'No evidence pack selected')}</p>
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
    </section>
  );
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}
