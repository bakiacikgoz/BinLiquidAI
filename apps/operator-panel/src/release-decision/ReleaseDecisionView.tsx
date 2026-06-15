import type { UiLocale } from '../i18n';
import { mapReleaseDecision, releaseDecisionBadges } from './releaseDecisionMappers';
import type { RcReleaseDecisionSnapshot } from './releaseDecisionTypes';

const copy = {
  en: {
    title: 'RC Release Decision',
    kicker: 'Release decision',
    lead: 'Hash-only dossier status, no-ship boundaries, and human sign-off state for Design Partner RC.',
    dossier: 'Dossier',
    summary: 'Summary',
    signoff: 'Human sign-off',
    hatA: 'Hat A',
    hatB: 'Hat B',
    designPartner: 'Design Partner RC',
    noShip: 'No-ship blockers',
    external: 'External blockers',
    refs: 'Evidence refs',
    blockers: 'Blocking reasons',
    warnings: 'Warnings',
    next: 'Next action',
    none: 'none',
    conditionalNext: 'Collect human sign-off before claiming final approval.',
    blockedNext: 'Keep release actions paused until blockers are resolved.',
    approvedNext: 'Eligible for human-reviewed Design Partner RC discussion, not public desktop release.',
  },
  tr: {
    title: 'RC Release Decision',
    kicker: 'Release karari',
    lead: 'Design Partner RC icin hash-only dossier durumu, no-ship sinirlari ve insan onayi.',
    dossier: 'Dossier',
    summary: 'Ozet',
    signoff: 'Insan onayi',
    hatA: 'Hat A',
    hatB: 'Hat B',
    designPartner: 'Design Partner RC',
    noShip: 'No-ship bloklayici',
    external: 'Dis bloklayici',
    refs: 'Evidence ref',
    blockers: 'Bloklayicilar',
    warnings: 'Uyarilar',
    next: 'Sonraki aksiyon',
    none: 'yok',
    conditionalNext: 'Final approval claiminden once insan onayini topla.',
    blockedNext: 'Bloklayicilar cozulene kadar release aksiyonlarini beklet.',
    approvedNext: 'Insan kontrollu Design Partner RC tartismasina uygun; public desktop release degil.',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function ReleaseDecisionView({
  snapshot,
  locale = 'en',
}: {
  snapshot?: RcReleaseDecisionSnapshot | null;
  locale?: UiLocale;
}) {
  const summary = mapReleaseDecision(snapshot);
  const text = copy[locale];
  const blockers = summary.blockingReasons.length > 0 ? summary.blockingReasons.join(', ') : text.none;
  const warnings = summary.warnings.length > 0 ? summary.warnings.join(', ') : text.none;
  const next = summary.status.includes('approved')
    ? text.approvedNext
    : summary.status === 'blocked'
      ? text.blockedNext
      : text.conditionalNext;

  return (
    <section className="workspace" data-testid="page-primary-region">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">{text.kicker}</p>
          <h2>{text.title}</h2>
          <p className="workspace-lead">{text.lead}</p>
        </div>
      </div>

      <div className="section-grid" data-testid="rc-release-decision">
        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{summary.status}</h3>
              <p>{text.designPartner}: {summary.designPartnerRcStatus}</p>
            </div>
          </div>
          <div className="reason-list" aria-label="RC release decision badges">
            {releaseDecisionBadges(summary).map((badge) => (
              <span className="reason-chip" data-tone={badge.tone} key={badge.label}>
                {badge.label}
              </span>
            ))}
          </div>
          <dl className="metric-list">
            <Row label={text.dossier} value={summary.latestDossierRef ?? text.none} />
            <Row label={text.summary} value={summary.latestSummaryRef ?? text.none} />
            <Row label={text.next} value={next} />
          </dl>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.signoff}</h3>
              <p>{summary.signoffStatus}</p>
            </div>
          </div>
          <dl className="metric-list">
            <Row label={text.hatA} value={summary.hatAStatus} />
            <Row label={text.hatB} value={summary.hatBStatus} />
            <Row label={text.noShip} value={String(summary.noShipBlockingCount)} />
            <Row label={text.external} value={String(summary.externalBlockerCount)} />
            <Row label={text.refs} value={String(summary.evidenceRefCount)} />
          </dl>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.blockers}</h3>
              <p>{text.warnings}</p>
            </div>
          </div>
          <dl className="metric-list">
            <Row label={text.blockers} value={blockers} />
            <Row label={text.warnings} value={warnings} />
          </dl>
        </article>
      </div>
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-row">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
