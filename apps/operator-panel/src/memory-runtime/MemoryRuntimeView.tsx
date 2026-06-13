import type { UiLocale } from '../i18n';
import type { MemoryRuntimeSnapshot, MemorySyncSnapshot } from '../control-plane/types';

const copy = {
  en: {
    kicker: 'Runtime Memory',
    title: 'Memory Runtime',
    lead: 'Prompt context injection and sync pack readiness without raw memory exposure.',
    runtime: 'Runtime bridge',
    sync: 'Sync pack',
    status: 'Status',
    contextBudget: 'Context budget',
    postRun: 'Post-run write',
    applyGate: 'Apply approval gate',
    crossEnv: 'Cross-environment import',
    evidence: 'Evidence',
    warnings: 'Warnings',
    none: 'none',
  },
  tr: {
    kicker: 'Runtime Memory',
    title: 'Memory Runtime',
    lead: 'Ham memory göstermeden prompt context injection ve sync pack hazırlığı.',
    runtime: 'Runtime bridge',
    sync: 'Sync pack',
    status: 'Durum',
    contextBudget: 'Context bütçesi',
    postRun: 'Run sonrası write',
    applyGate: 'Apply onay kapısı',
    crossEnv: 'Ortamlar arası import',
    evidence: 'Evidence',
    warnings: 'Uyarılar',
    none: 'yok',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function MemoryRuntimeView({
  runtime,
  sync,
  locale = 'en',
}: {
  runtime?: MemoryRuntimeSnapshot | null;
  sync?: MemorySyncSnapshot | null;
  locale?: UiLocale;
}) {
  const text = copy[locale];
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
        <article className="page-card" data-testid="memory-runtime-evidence">
          <div className="page-card-header">
            <div>
              <h3>{text.runtime}</h3>
              <p>{runtime?.enabled ? 'enabled' : 'disabled'}</p>
            </div>
          </div>
          <dl className="metric-list">
            <Row label={text.status} value={runtime?.status ?? 'disabled'} />
            <Row
              label={text.contextBudget}
              value={`${runtime?.contextTopK ?? 0} / ${runtime?.maxContextChars ?? 0}`}
            />
            <Row label={text.postRun} value={runtime?.postRunWriteEnabled ? 'enabled' : 'disabled'} />
            <Row label={text.evidence} value={runtime?.lastEvidenceRef ?? text.none} />
            <Row label={text.warnings} value={(runtime?.warnings ?? []).join(', ') || text.none} />
          </dl>
        </article>

        <article className="page-card" data-testid="memory-sync-status">
          <div className="page-card-header">
            <div>
              <h3>{text.sync}</h3>
              <p>{sync?.enabled ? 'enabled' : 'disabled'}</p>
            </div>
          </div>
          <dl className="metric-list">
            <Row label={text.status} value={sync?.status ?? 'disabled'} />
            <Row label={text.applyGate} value={sync?.importApplyRequiresApproval ? 'required' : 'optional'} />
            <Row label={text.crossEnv} value={sync?.allowCrossEnvironmentImport ? 'allowed' : 'blocked'} />
            <Row label={text.evidence} value={sync?.lastPackRef ?? text.none} />
            <Row label={text.warnings} value={(sync?.warnings ?? []).join(', ') || text.none} />
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
