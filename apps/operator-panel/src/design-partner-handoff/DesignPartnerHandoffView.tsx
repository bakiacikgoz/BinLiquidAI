import type { UiLocale } from '../i18n';
import { handoffBadges, mapDesignPartnerHandoff } from './designPartnerHandoffMappers';
import type { DesignPartnerHandoffSnapshot } from './designPartnerHandoffTypes';

const copy = {
  en: {
    title: 'Design Partner Handoff',
    lead: 'Operator-facing RC handoff status across release train, field evidence, first-run drill, support, and claim boundaries.',
    kicker: 'Release handoff',
    status: 'Status',
    releaseTrain: 'Release train',
    firstRun: 'First-run drill',
    pack: 'Handoff pack',
    claims: 'Claim boundaries',
    blockers: 'Blockers',
    warnings: 'Warnings',
    next: 'Next action',
    checklist: 'Operator checklist',
    none: 'none',
    missing: 'not generated',
    notReady: 'Not ready because blockers or warnings remain.',
    ready: 'Ready for controlled design partner handoff.',
  },
  tr: {
    title: 'Design Partner Handoff',
    lead: 'Release train, field evidence, first-run drill, destek ve claim sınırları için operatör odaklı RC handoff durumu.',
    kicker: 'Release handoff',
    status: 'Durum',
    releaseTrain: 'Release train',
    firstRun: 'First-run drill',
    pack: 'Handoff pack',
    claims: 'Claim sınırları',
    blockers: 'Bloklayıcılar',
    warnings: 'Uyarılar',
    next: 'Sonraki aksiyon',
    checklist: 'Operatör checklist',
    none: 'yok',
    missing: 'üretilmedi',
    notReady: 'Hazır değil; blocker veya warning kalmış durumda.',
    ready: 'Kontrollü design partner handoff için hazır.',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function DesignPartnerHandoffView({
  snapshot,
  locale = 'en',
}: {
  snapshot?: DesignPartnerHandoffSnapshot | null;
  locale?: UiLocale;
}) {
  const text = copy[locale];
  const summary = mapDesignPartnerHandoff(snapshot);
  const blockers = summary.blockers.length > 0 ? summary.blockers.join(', ') : text.none;
  const warnings = summary.warnings.length > 0 ? summary.warnings.join(', ') : text.none;
  const claimRows = Object.entries(summary.claimBoundarySummary);

  return (
    <section className="workspace" data-testid="page-primary-region">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">{text.kicker}</p>
          <h2>{text.title}</h2>
          <p className="workspace-lead">{text.lead}</p>
        </div>
      </div>

      <div className="section-grid" data-testid="design-partner-handoff">
        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{summary.status === 'missing' ? text.missing : summary.status}</h3>
              <p>{summary.lastGeneratedAtUtc ?? text.none}</p>
            </div>
          </div>
          <div className="reason-list" aria-label="Design partner handoff badges">
            {handoffBadges(summary).map((badge) => (
              <span className="reason-chip" data-tone={badge.tone} key={badge.label}>
                {badge.label}
              </span>
            ))}
          </div>
          <dl className="metric-list">
            <Row label={text.pack} value={summary.handoffPackPath ?? text.none} />
            <Row label={text.next} value={summary.status === 'ready' ? text.ready : text.notReady} />
          </dl>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.status}</h3>
              <p>{text.releaseTrain} · {text.firstRun}</p>
            </div>
          </div>
          <dl className="metric-list">
            <Row label={text.releaseTrain} value={summary.releaseTrainStatus} />
            <Row label={text.firstRun} value={summary.firstRunDrillStatus} />
          </dl>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.claims}</h3>
              <p>{claimRows.length}</p>
            </div>
          </div>
          <dl className="metric-list">
            {claimRows.map(([label, value]) => (
              <Row label={label} value={value} key={label} />
            ))}
          </dl>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.checklist}</h3>
              <p>{summary.status === 'ready' ? text.ready : text.notReady}</p>
            </div>
          </div>
          <ul className="compact-list">
            <li>release handoff verify</li>
            <li>review CLAIM_BOUNDARY_CARD.md</li>
            <li>run pilot ops drill</li>
            <li>stop on blocked status</li>
          </ul>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.blockers}</h3>
              <p>{blockers}</p>
            </div>
          </div>
          <dl className="metric-list">
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
