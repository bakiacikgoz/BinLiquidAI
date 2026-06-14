import type { UiLocale } from '../i18n';
import { fieldEvidenceBadges, mapDesignPartnerFieldEvidence } from './designPartnerFieldMappers';
import type { DesignPartnerFieldEvidenceSnapshot } from './designPartnerFieldTypes';

const copy = {
  en: {
    title: 'Design Partner Field Evidence',
    lead: 'Target-environment evidence closure bound to independent operator attestation and strict RC promotion.',
    kicker: 'Evidence',
    session: 'Session',
    mode: 'Mode',
    items: 'Items',
    bundle: 'Bundle',
    attestation: 'Attestation',
    promotion: 'Strict RC promotion',
    blockedClaims: 'Blocked claim boundaries',
    blockers: 'Blockers',
    warnings: 'Warnings',
    none: 'none',
    missing: 'not collected',
  },
  tr: {
    title: 'Design Partner Field Evidence',
    lead: 'Bağımsız operatör attestation ve strict RC promotion ile bağlanmış target-environment evidence kapanışı.',
    kicker: 'Evidence',
    session: 'Session',
    mode: 'Mod',
    items: 'Kalemler',
    bundle: 'Bundle',
    attestation: 'Attestation',
    promotion: 'Strict RC promotion',
    blockedClaims: 'Bloke claim sınırları',
    blockers: 'Bloklayıcılar',
    warnings: 'Uyarılar',
    none: 'yok',
    missing: 'toplanmadı',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function DesignPartnerFieldEvidenceView({
  snapshot,
  locale = 'en',
}: {
  snapshot?: DesignPartnerFieldEvidenceSnapshot | null;
  locale?: UiLocale;
}) {
  const text = copy[locale];
  const summary = mapDesignPartnerFieldEvidence(snapshot);
  const blockedClaims = summary.blockedClaims.length > 0 ? summary.blockedClaims : [text.none];
  const blockers = summary.blockingReasons.length > 0 ? summary.blockingReasons.join(', ') : text.none;
  const warnings = summary.warnings.length > 0 ? summary.warnings.join(', ') : text.none;

  return (
    <section className="workspace" data-testid="page-primary-region">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">{text.kicker}</p>
          <h2>{text.title}</h2>
          <p className="workspace-lead">{text.lead}</p>
        </div>
      </div>

      <div className="section-grid" data-testid="design-partner-field-evidence">
        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{summary.status === 'missing' ? text.missing : summary.status}</h3>
              <p>{summary.generatedAtUtc}</p>
            </div>
          </div>
          <div className="reason-list" aria-label="Field evidence safety badges">
            {fieldEvidenceBadges(summary).map((badge) => (
              <span className="reason-chip" data-tone={badge.tone} key={badge.label}>
                {badge.label}
              </span>
            ))}
          </div>
          <dl className="metric-list">
            <Row label={text.session} value={summary.sessionId ?? text.none} />
            <Row label={text.mode} value={summary.mode ?? text.none} />
            <Row label={text.items} value={String(summary.itemCount)} />
          </dl>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.bundle}</h3>
              <p>{summary.latestBundlePath ?? text.none}</p>
            </div>
          </div>
          <dl className="metric-list">
            <Row label={text.attestation} value={summary.attestationStatus} />
            <Row label={text.promotion} value={summary.strictRcStatus} />
          </dl>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.blockedClaims}</h3>
              <p>{blockedClaims.length === 1 && blockedClaims[0] === text.none ? text.none : `${blockedClaims.length}`}</p>
            </div>
          </div>
          <ul className="compact-list">
            {blockedClaims.map((claim) => (
              <li key={claim}>{claim}</li>
            ))}
          </ul>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.promotion}</h3>
              <p>{summary.latestPromotionPath ?? text.none}</p>
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
