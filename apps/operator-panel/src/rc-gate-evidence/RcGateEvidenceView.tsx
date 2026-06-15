import type { UiLocale } from '../i18n';
import { mapRcGateEvidence, rcGateEvidenceBadges } from './rcGateEvidenceMappers';
import type { RcGateEvidenceSnapshot } from './rcGateEvidenceTypes';

const copy = {
  en: {
    title: 'RC Gate Evidence',
    kicker: 'Release evidence',
    lead: 'Cross-platform gate ledger, artifact completeness, and claim-safe RC readiness without relying on Makefile.',
    ledger: 'Ledger',
    verification: 'Verification',
    gates: 'Verified gates',
    missingGates: 'Missing gates',
    missingArtifacts: 'Missing artifacts',
    make: 'Make required',
    ready: 'Ready for RC freeze',
    blockers: 'Blocking reasons',
    warnings: 'Warnings',
    scans: 'Secret/raw scan',
    next: 'Next action',
    none: 'none',
    yes: 'yes',
    no: 'no',
    readyNext: 'Proceed to human-reviewed RC freeze decision.',
    blockedNext: 'Keep release actions paused until gate evidence is repaired.',
  },
  tr: {
    title: 'RC Gate Evidence',
    kicker: 'Release kaniti',
    lead: 'Makefile bagimliligi olmadan cross-platform gate ledger, artifact tamligi ve claim-safe RC hazirligi.',
    ledger: 'Ledger',
    verification: 'Dogrulama',
    gates: 'Dogrulanan gate',
    missingGates: 'Eksik gate',
    missingArtifacts: 'Eksik artifact',
    make: 'Make gerekli',
    ready: 'RC freeze hazir',
    blockers: 'Bloklayicilar',
    warnings: 'Uyarilar',
    scans: 'Secret/raw taramasi',
    next: 'Sonraki aksiyon',
    none: 'yok',
    yes: 'evet',
    no: 'hayir',
    readyNext: 'Insan onayli RC freeze kararina gecilebilir.',
    blockedNext: 'Gate evidence onarilana kadar release aksiyonlarini beklet.',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function RcGateEvidenceView({
  snapshot,
  locale = 'en',
}: {
  snapshot?: RcGateEvidenceSnapshot | null;
  locale?: UiLocale;
}) {
  const summary = mapRcGateEvidence(snapshot);
  const text = copy[locale];
  const blockers = summary.blockingReasons.length > 0 ? summary.blockingReasons.join(', ') : text.none;
  const warnings = summary.warnings.length > 0 ? summary.warnings.join(', ') : text.none;
  const yes = locale === 'tr' ? text.yes : 'yes';
  const no = locale === 'tr' ? text.no : 'no';

  return (
    <section className="workspace" data-testid="page-primary-region">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">{text.kicker}</p>
          <h2>{text.title}</h2>
          <p className="workspace-lead">{text.lead}</p>
        </div>
      </div>

      <div className="section-grid" data-testid="rc-gate-evidence">
        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{summary.status}</h3>
              <p>{summary.target}</p>
            </div>
          </div>
          <div className="reason-list" aria-label="RC gate evidence badges">
            {rcGateEvidenceBadges(summary).map((badge) => (
              <span className="reason-chip" data-tone={badge.tone} key={badge.label}>
                {badge.label}
              </span>
            ))}
          </div>
          <dl className="metric-list">
            <Row label={text.ledger} value={summary.latestLedgerRef ?? text.none} />
            <Row label={text.verification} value={summary.latestVerificationRef ?? text.none} />
            <Row label={text.next} value={summary.readyForRcFreeze ? text.readyNext : text.blockedNext} />
          </dl>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.gates}</h3>
              <p>{summary.platform}</p>
            </div>
          </div>
          <dl className="metric-list">
            <Row label={text.gates} value={String(summary.verifiedGateCount)} />
            <Row label={text.missingGates} value={String(summary.missingGateCount)} />
            <Row label={text.missingArtifacts} value={String(summary.missingArtifactCount)} />
            <Row label={text.make} value={`Make required: ${summary.makeRequired ? yes : no}`} />
            <Row label={text.ready} value={`Ready for RC freeze: ${summary.readyForRcFreeze ? yes : no}`} />
          </dl>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.scans}</h3>
              <p>{summary.secretScanStatus} / {summary.rawMarkerScanStatus}</p>
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
