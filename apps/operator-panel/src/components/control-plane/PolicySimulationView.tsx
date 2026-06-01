import { formatReasonCode } from '../../control-plane/reasonCodes';
import type { UiLocale } from '../../i18n';

export function PolicySimulationView({ simulation, locale = 'en' }: { simulation: unknown; locale?: UiLocale }) {
  const record = asRecord(simulation);
  const decisions = Array.isArray(record.decisions) ? record.decisions : [];
  return (
    <section className="workspace" data-testid="page-primary-region">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">Policy</p>
          <h2>Policy Simulation</h2>
          <p className="workspace-lead">{String(record.overall_status ?? 'not evaluated')}</p>
        </div>
      </div>
      <div className="run-list">
        {decisions.length > 0 ? (
          decisions.map((item) => {
            const decision = asRecord(item);
            const reasonCode = typeof decision.reason_code === 'string' ? decision.reason_code : '';
            return (
              <article className="run-list-item" key={String(decision.action_id)}>
                <strong>{String(decision.action_id ?? '-')}</strong>
                <span>{String(decision.decision_action ?? '-')}</span>
                <small>{reasonCode ? formatReasonCode(reasonCode, locale) : '-'}</small>
              </article>
            );
          })
        ) : (
          <article className="run-list-item">
            <strong>No simulation loaded</strong>
            <span>Select an agent or refresh the control-plane context to run the default dry-run.</span>
            <small>dry-run only</small>
          </article>
        )}
      </div>
      <div className="section-grid two-up">
        <article className="page-card">
          <h3>Policy pack</h3>
          <div className="metric-list">
            <div className="metric-row">
              <span>Status</span>
              <strong>{String(record.overall_status ?? 'not evaluated')}</strong>
            </div>
            <div className="metric-row">
              <span>Mutation handling</span>
              <strong>approval required</strong>
            </div>
            <div className="metric-row">
              <span>Unsafe classes</span>
              <strong>deny by default</strong>
            </div>
          </div>
        </article>
        <article className="page-card">
          <h3>Reason code glossary</h3>
          <div className="run-list">
            <article className="run-list-item">
              <strong>POLICY_ALLOW</strong>
              <span>Read-only or harmless action is allowed.</span>
              <small>allow</small>
            </article>
            <article className="run-list-item">
              <strong>APPROVAL_REQUIRED</strong>
              <span>Mutation can continue only through approval lifecycle.</span>
              <small>require approval</small>
            </article>
            <article className="run-list-item">
              <strong>POLICY_DENY</strong>
              <span>Credential, destructive, financial, or unknown action is blocked.</span>
              <small>deny</small>
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
