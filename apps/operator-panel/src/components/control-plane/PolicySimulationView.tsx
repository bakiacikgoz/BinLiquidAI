import { formatReasonCode } from '../../control-plane/reasonCodes';
import type { UiLocale } from '../../i18n';
import { CodeToken, ReasonChip, StatusBadge } from '../primitives/Token';

const copy = {
  en: {
    kicker: 'Policy',
    title: 'Policy Simulation',
    notEvaluated: 'not evaluated',
    noSimulationLoaded: 'No simulation loaded',
    noSimulationBody: 'Select an agent or refresh the control-plane context to run the default dry-run.',
    dryRunOnly: 'dry-run only',
    policyPack: 'Policy pack',
    status: 'Status',
    mutationHandling: 'Mutation handling',
    approvalRequired: 'approval required',
    unsafeClasses: 'Unsafe classes',
    denyByDefault: 'deny by default',
    glossary: 'Reason code glossary',
    allowDescription: 'Read-only or harmless action is allowed.',
    approvalDescription: 'Mutation can continue only through approval lifecycle.',
    denyDescription: 'Credential, destructive, financial, or unknown action is blocked.',
    allow: 'allow',
    requireApproval: 'require approval',
    deny: 'deny',
  },
  tr: {
    kicker: 'Policy',
    title: 'Policy simülasyonu',
    notEvaluated: 'değerlendirilmedi',
    noSimulationLoaded: 'Simülasyon yüklenmedi',
    noSimulationBody: 'Varsayılan dry-run için bir agent seçin veya control-plane bağlamını yenileyin.',
    dryRunOnly: 'yalnızca dry-run',
    policyPack: 'Policy pack',
    status: 'Durum',
    mutationHandling: 'Mutasyon yönetimi',
    approvalRequired: 'onay gerekli',
    unsafeClasses: 'Güvensiz sınıflar',
    denyByDefault: 'varsayılan olarak reddet',
    glossary: 'Reason code sözlüğü',
    allowDescription: 'Salt okunur veya zararsız aksiyonlara izin verilir.',
    approvalDescription: 'Mutasyon yalnızca onay yaşam döngüsü üzerinden devam edebilir.',
    denyDescription: 'Kimlik bilgisi, yıkıcı, finansal veya bilinmeyen aksiyon blokelenir.',
    allow: 'izin ver',
    requireApproval: 'onay iste',
    deny: 'reddet',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function PolicySimulationView({ simulation, locale = 'en' }: { simulation: unknown; locale?: UiLocale }) {
  const text = copy[locale];
  const record = asRecord(simulation);
  const decisions = Array.isArray(record.decisions) ? record.decisions : [];
  const overallStatus = String(record.overall_status ?? text.notEvaluated);
  return (
    <section className="workspace" data-testid="page-primary-region">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">{text.kicker}</p>
          <h2>{text.title}</h2>
          <p className="workspace-lead">{overallStatus}</p>
        </div>
      </div>
      <div className="run-list">
        {decisions.length > 0 ? (
          decisions.map((item) => {
            const decision = asRecord(item);
            const reasonCode = typeof decision.reason_code === 'string' ? decision.reason_code : '';
            return (
              <article className="run-list-item" key={String(decision.action_id)}>
                <div className="run-list-main">
                  <strong>{String(decision.action_id ?? '-')}</strong>
                  <div className="run-list-meta">
                    <CodeToken>{String(decision.decision_action ?? '-')}</CodeToken>
                    {reasonCode ? <ReasonChip title={formatReasonCode(reasonCode, locale)}>{reasonCode}</ReasonChip> : null}
                  </div>
                </div>
                <StatusBadge tone={String(decision.decision_action).includes('deny') ? 'error' : 'success'}>
                  {String(decision.decision_action ?? '-')}
                </StatusBadge>
              </article>
            );
          })
        ) : (
          <article className="run-list-item">
            <div className="run-list-main">
              <strong>{text.noSimulationLoaded}</strong>
              <span>{text.noSimulationBody}</span>
            </div>
            <StatusBadge tone="muted">{text.dryRunOnly}</StatusBadge>
          </article>
        )}
      </div>
      <div className="section-grid two-up">
        <article className="page-card">
          <h3>{text.policyPack}</h3>
          <div className="metric-list">
            <div className="metric-row">
              <span>{text.status}</span>
              <strong>{overallStatus}</strong>
            </div>
            <div className="metric-row">
              <span>{text.mutationHandling}</span>
              <strong>{text.approvalRequired}</strong>
            </div>
            <div className="metric-row">
              <span>{text.unsafeClasses}</span>
              <strong>{text.denyByDefault}</strong>
            </div>
          </div>
        </article>
        <article className="page-card">
          <h3>{text.glossary}</h3>
          <div className="run-list">
            <article className="run-list-item">
              <div className="run-list-main">
                <strong>POLICY_ALLOW</strong>
                <span>{text.allowDescription}</span>
              </div>
              <StatusBadge tone="success">{text.allow}</StatusBadge>
            </article>
            <article className="run-list-item">
              <div className="run-list-main">
                <strong>APPROVAL_REQUIRED</strong>
                <span>{text.approvalDescription}</span>
              </div>
              <StatusBadge tone="warning">{text.requireApproval}</StatusBadge>
            </article>
            <article className="run-list-item">
              <div className="run-list-main">
                <strong>POLICY_DENY</strong>
                <span>{text.denyDescription}</span>
              </div>
              <StatusBadge tone="error">{text.deny}</StatusBadge>
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
