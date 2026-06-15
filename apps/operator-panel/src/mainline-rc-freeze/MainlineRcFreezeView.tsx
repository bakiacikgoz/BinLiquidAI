import type { UiLocale } from '../i18n';
import { mainlineRcFreezeBadges, mapMainlineRcFreeze } from './mainlineRcFreezeMappers';
import type { MainlineRcFreezeSnapshot } from './mainlineRcFreezeTypes';

const copy = {
  en: {
    title: 'Mainline RC Freeze',
    lead: 'Non-destructive mainline rehearsal and RC freeze evidence for the stacked Design Partner release chain.',
    kicker: 'Release freeze',
    status: 'Status',
    stack: 'Stack graph',
    rehearsal: 'Merge rehearsal',
    gates: 'Gate evidence',
    scan: 'Artifact scan',
    manifest: 'Freeze manifest',
    evidence: 'Evidence mode',
    raw: 'Raw persistence',
    blockers: 'Blockers',
    warnings: 'Warnings',
    next: 'Next action',
    none: 'none',
    missing: 'not generated',
    ready: 'Eligible for human-reviewed stacked PR merge sequencing.',
    notReady: 'Keep merge/release actions paused until blockers and warnings are reviewed.',
  },
  tr: {
    title: 'Mainline RC Freeze',
    lead: 'Stacked Design Partner release zinciri için destructive olmayan mainline rehearsal ve RC freeze kanıtı.',
    kicker: 'Release freeze',
    status: 'Durum',
    stack: 'Stack grafiği',
    rehearsal: 'Merge rehearsal',
    gates: 'Gate kanıtı',
    scan: 'Artifact taraması',
    manifest: 'Freeze manifest',
    evidence: 'Kanıt modu',
    raw: 'Raw persistence',
    blockers: 'Bloklayıcılar',
    warnings: 'Uyarılar',
    next: 'Sonraki aksiyon',
    none: 'yok',
    missing: 'üretilmedi',
    ready: 'İnsan onaylı stacked PR merge sırası için aday.',
    notReady: 'Blocker ve warning gözden geçirilene kadar merge/release aksiyonları bekletilmeli.',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function MainlineRcFreezeView({
  snapshot,
  locale = 'en',
}: {
  snapshot?: MainlineRcFreezeSnapshot | null;
  locale?: UiLocale;
}) {
  const text = copy[locale];
  const summary = mapMainlineRcFreeze(snapshot);
  const blockers = summary.blockers.length > 0 ? summary.blockers.join(', ') : text.none;
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

      <div className="section-grid" data-testid="mainline-rc-freeze">
        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{summary.status === 'missing' ? text.missing : summary.status}</h3>
              <p>{summary.freezeId ?? summary.lastGeneratedAtUtc ?? text.none}</p>
            </div>
          </div>
          <div className="reason-list" aria-label="Mainline RC freeze badges">
            {mainlineRcFreezeBadges(summary).map((badge) => (
              <span className="reason-chip" data-tone={badge.tone} key={badge.label}>
                {badge.label}
              </span>
            ))}
          </div>
          <dl className="metric-list">
            <Row label={text.manifest} value={summary.manifestPath ?? text.none} />
            <Row label={text.next} value={summary.status === 'ready' ? text.ready : text.notReady} />
          </dl>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.status}</h3>
              <p>{text.stack} / {text.rehearsal}</p>
            </div>
          </div>
          <dl className="metric-list">
            <Row label={text.stack} value={summary.stackStatus} />
            <Row label={text.rehearsal} value={summary.mergeRehearsalStatus} />
            <Row label={text.gates} value={summary.gateEvidenceStatus} />
            <Row label={text.scan} value={summary.artifactScanStatus} />
          </dl>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.evidence}</h3>
              <p>{summary.evidenceMode}</p>
            </div>
          </div>
          <dl className="metric-list">
            <Row label={text.raw} value={`raw persistence ${String(summary.rawPersistence)}`} />
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
