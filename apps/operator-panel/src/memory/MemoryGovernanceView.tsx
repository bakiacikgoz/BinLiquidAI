import type { UiLocale } from '../i18n';
import type { MemoryAuthoritySnapshot } from '../control-plane/types';
import { mapMemoryGovernance } from './memoryMappers';

const copy = {
  en: {
    kicker: 'Governed Memory',
    title: 'Memory Governance',
    lead: 'Scoped memory authority, redacted evidence and index readiness.',
    status: 'Authority status',
    scopeTitle: 'Scope records',
    signalTitle: 'Governance signals',
    warnings: 'Warnings',
    blockers: 'Blocking reasons',
    none: 'none',
  },
  tr: {
    kicker: 'Yönetişimli Memory',
    title: 'Memory Yönetişimi',
    lead: 'Scope bazlı memory otoritesi, redacted evidence ve index hazırlığı.',
    status: 'Otorite durumu',
    scopeTitle: 'Scope kayıtları',
    signalTitle: 'Yönetişim sinyalleri',
    warnings: 'Uyarılar',
    blockers: 'Engelleyici nedenler',
    none: 'yok',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function MemoryGovernanceView({
  snapshot,
  locale = 'en',
}: {
  snapshot?: MemoryAuthoritySnapshot | null;
  locale?: UiLocale;
}) {
  const text = copy[locale];
  const model = mapMemoryGovernance(snapshot);

  return (
    <section className="workspace" data-testid="page-primary-region">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">{text.kicker}</p>
          <h2>{text.title}</h2>
          <p className="workspace-lead">{text.lead}</p>
        </div>
      </div>

      <div className="metric-grid">
        <article className="metric-card">
          <h3>{text.status}</h3>
          <p className="metric">{model.status}</p>
          <small>{model.generatedDetail}</small>
        </article>
        {model.metrics.map((metric) => (
          <article className="metric-card" key={metric.label}>
            <h3>{metric.label}</h3>
            <p className="metric">{metric.value}</p>
            <small>{metric.detail}</small>
          </article>
        ))}
      </div>

      <div className="section-grid two-up">
        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.signalTitle}</h3>
              <p>{model.status}</p>
            </div>
          </div>
          <div className="reason-list" aria-label="Memory governance badges">
            {model.badges.map((badge) => (
              <span className="reason-chip" data-tone={badge.tone} key={badge.label}>
                {badge.label}
              </span>
            ))}
          </div>
          <dl className="metric-list">
            <div className="metric-row">
              <dt>{text.warnings}</dt>
              <dd>{model.warnings.length > 0 ? model.warnings.join(', ') : text.none}</dd>
            </div>
            <div className="metric-row">
              <dt>{text.blockers}</dt>
              <dd>{model.blockingReasons.length > 0 ? model.blockingReasons.join(', ') : text.none}</dd>
            </div>
          </dl>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.scopeTitle}</h3>
              <p>{snapshot?.index.backend ?? 'sqlite_text'}</p>
            </div>
          </div>
          <div className="run-list">
            {model.rows.map((row) => (
              <article className="run-list-item" key={row.id}>
                <strong>{row.label}</strong>
                <span>{row.meta}</span>
                <small>{row.status}</small>
              </article>
            ))}
          </div>
        </article>
      </div>
    </section>
  );
}
