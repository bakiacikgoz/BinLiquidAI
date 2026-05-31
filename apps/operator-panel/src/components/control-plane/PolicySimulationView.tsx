export function PolicySimulationView({ simulation }: { simulation: unknown }) {
  const record = asRecord(simulation);
  const decisions = Array.isArray(record.decisions) ? record.decisions : [];
  return (
    <section className="workspace">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">Policy</p>
          <h2>Policy Simulation</h2>
          <p className="workspace-lead">{String(record.overall_status ?? 'not evaluated')}</p>
        </div>
      </div>
      <div className="run-list">
        {decisions.map((item) => {
          const decision = asRecord(item);
          return (
            <article className="run-list-item" key={String(decision.action_id)}>
              <strong>{String(decision.action_id ?? '-')}</strong>
              <span>{String(decision.decision_action ?? '-')}</span>
              <small>{String(decision.reason_code ?? '-')}</small>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}
