import { formatReasonCode } from '../../control-plane/reasonCodes';
import type { UiLocale } from '../../i18n';

export function ExecutionSurfacesView({
  computerUseCapability,
  locale = 'en',
}: {
  computerUseCapability: unknown;
  locale?: UiLocale;
}) {
  const capability = asRecord(computerUseCapability);
  const computerUseReason =
    typeof capability.reasonCode === 'string' ? capability.reasonCode : 'COMPUTER_USE_CLAIM_BLOCKED';
  return (
    <section className="workspace" data-testid="page-primary-region">
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
          <small>{formatReasonCode(computerUseReason, locale)}</small>
          <div className="warning-inline">Live start disabled until qualification evidence is present.</div>
        </article>
        <article className="page-card">
          <h3>Public desktop installer</h3>
          <p className="metric">blocked</p>
          <small>{formatReasonCode('HAT_B_EVIDENCE_MISSING', locale)}</small>
        </article>
        <article className="page-card">
          <h3>External adapters</h3>
          <p className="metric">contract only</p>
          <small>adapter evaluation required before execution</small>
        </article>
        <article className="page-card">
          <h3>Qualification checklist</h3>
          <div className="metric-list">
            <div className="metric-row">
              <span>Signed platform evidence</span>
              <strong>missing</strong>
            </div>
            <div className="metric-row">
              <span>Replay verification</span>
              <strong>required</strong>
            </div>
            <div className="metric-row">
              <span>Supervised opt-in</span>
              <strong>required</strong>
            </div>
          </div>
        </article>
      </div>
    </section>
  );
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}
