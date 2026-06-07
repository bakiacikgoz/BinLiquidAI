import { formatReasonCode } from '../../control-plane/reasonCodes';
import type { UiLocale } from '../../i18n';

const copy = {
  en: {
    kicker: 'Execution Boundaries',
    title: 'Execution Surfaces',
    lead: 'Live surfaces stay disabled unless qualification evidence is present.',
    coreRuntime: 'Core Runtime',
    ready: 'ready',
    teamRuntime: 'Team Runtime',
    teamRuntimeState: 'pilot / enterprise gated',
    computerUse: 'Computer-use',
    blocked: 'blocked',
    liveDisabled: 'Live start disabled until qualification evidence is present.',
    publicInstaller: 'Public desktop installer',
    externalAdapters: 'External adapters',
    contractOnly: 'contract only',
    adapterRequired: 'adapter evaluation required before execution',
    checklist: 'Qualification checklist',
    signedEvidence: 'Signed platform evidence',
    missing: 'missing',
    replayVerification: 'Replay verification',
    required: 'required',
    supervisedOptIn: 'Supervised opt-in',
  },
  tr: {
    kicker: 'Yürütme sınırları',
    title: 'Yürütme yüzeyleri',
    lead: 'Qualification evidence yoksa live yüzeyler kapalı kalır.',
    coreRuntime: 'Core runtime',
    ready: 'hazır',
    teamRuntime: 'Team runtime',
    teamRuntimeState: 'pilot / enterprise kapılı',
    computerUse: 'Computer-use',
    blocked: 'bloke',
    liveDisabled: 'Qualification evidence gelene kadar live başlangıç kapalı.',
    publicInstaller: 'Public desktop installer',
    externalAdapters: 'Harici adapterlar',
    contractOnly: 'yalnızca sözleşme',
    adapterRequired: 'yürütmeden önce adapter değerlendirmesi gerekli',
    checklist: 'Qualification checklist',
    signedEvidence: 'İmzalı platform evidence',
    missing: 'eksik',
    replayVerification: 'Replay doğrulaması',
    required: 'gerekli',
    supervisedOptIn: 'Supervised opt-in',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function ExecutionSurfacesView({
  computerUseCapability,
  locale = 'en',
}: {
  computerUseCapability: unknown;
  locale?: UiLocale;
}) {
  const text = copy[locale];
  const capability = asRecord(computerUseCapability);
  const computerUseReason =
    typeof capability.reasonCode === 'string' ? capability.reasonCode : 'COMPUTER_USE_CLAIM_BLOCKED';
  return (
    <section className="workspace" data-testid="page-primary-region">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">{text.kicker}</p>
          <h2>{text.title}</h2>
          <p className="workspace-lead">{text.lead}</p>
        </div>
      </div>
      <div className="section-grid two-up">
        <article className="page-card">
          <h3>{text.coreRuntime}</h3>
          <p className="metric">{text.ready}</p>
        </article>
        <article className="page-card">
          <h3>{text.teamRuntime}</h3>
          <p className="metric">{text.teamRuntimeState}</p>
        </article>
        <article className="page-card">
          <h3>{text.computerUse}</h3>
          <p className="metric">{String(capability.status ?? text.blocked)}</p>
          <small>{formatReasonCode(computerUseReason, locale)}</small>
          <div className="warning-inline">{text.liveDisabled}</div>
        </article>
        <article className="page-card">
          <h3>{text.publicInstaller}</h3>
          <p className="metric">{text.blocked}</p>
          <small>{formatReasonCode('HAT_B_EVIDENCE_MISSING', locale)}</small>
        </article>
        <article className="page-card">
          <h3>{text.externalAdapters}</h3>
          <p className="metric">{text.contractOnly}</p>
          <small>{text.adapterRequired}</small>
        </article>
        <article className="page-card">
          <h3>{text.checklist}</h3>
          <div className="metric-list">
            <div className="metric-row">
              <span>{text.signedEvidence}</span>
              <strong>{text.missing}</strong>
            </div>
            <div className="metric-row">
              <span>{text.replayVerification}</span>
              <strong>{text.required}</strong>
            </div>
            <div className="metric-row">
              <span>{text.supervisedOptIn}</span>
              <strong>{text.required}</strong>
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
