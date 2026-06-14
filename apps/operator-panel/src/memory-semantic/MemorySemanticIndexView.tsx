import type { MemorySemanticIndexSnapshot } from '../control-plane/types';
import type { UiLocale } from '../i18n';

const copy = {
  en: {
    kicker: 'Semantic Memory',
    title: 'Semantic Index',
    lead: 'Index readiness, retrieval quality and backend posture without raw memory or query payloads.',
    index: 'Index',
    backend: 'Backend',
    status: 'Status',
    runtime: 'Runtime injection',
    profile: 'Embedding profile',
    records: 'Records',
    shards: 'Workspace shards',
    quality: 'Last evaluation',
    raw: 'Raw persistence',
    experimental: 'Experimental backends',
    blockers: 'Reason codes',
    disabled: 'disabled',
    enabled: 'enabled',
    none: 'none',
    blocked: 'blocked',
  },
  tr: {
    kicker: 'Semantic Memory',
    title: 'Semantic Index',
    lead: 'Ham memory veya query payload göstermeden indeks, retrieval kalite ve backend durumu.',
    index: 'Index',
    backend: 'Backend',
    status: 'Durum',
    runtime: 'Runtime injection',
    profile: 'Embedding profili',
    records: 'Kayıt',
    shards: 'Workspace shard',
    quality: 'Son değerlendirme',
    raw: 'Raw persistence',
    experimental: 'Experimental backend',
    blockers: 'Reason code',
    disabled: 'disabled',
    enabled: 'enabled',
    none: 'yok',
    blocked: 'kapalı',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function MemorySemanticIndexView({
  snapshot,
  locale = 'en',
}: {
  snapshot?: MemorySemanticIndexSnapshot | null;
  locale?: UiLocale;
}) {
  const text = copy[locale];
  const value = snapshot ?? emptySnapshot();
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
        <article className="page-card" data-testid="memory-semantic-status">
          <div className="page-card-header">
            <div>
              <h3>{text.index}</h3>
              <p>{value.status}</p>
            </div>
          </div>
          <dl className="metric-list">
            <Row label={text.status} value={value.status} />
            <Row label={text.runtime} value={value.runtimeInjectionEnabled ? text.enabled : text.disabled} />
            <Row label={text.profile} value={value.embeddingProfile} />
            <Row label={text.records} value={String(value.recordCount)} />
            <Row label={text.shards} value={String(value.workspaceShardCount)} />
            <Row label={text.quality} value={value.lastEvaluationStatus} />
          </dl>
        </article>

        <article className="page-card" data-testid="memory-semantic-backend">
          <div className="page-card-header">
            <div>
              <h3>{text.backend}</h3>
              <p>{value.defaultBackend}</p>
            </div>
          </div>
          <dl className="metric-list">
            <Row label={text.raw} value={value.rawPersistence ? text.enabled : text.blocked} />
            <Row label={text.experimental} value={formatMap(value.experimentalBackends) || text.none} />
            <Row label={text.backend} value={formatMap(value.backendStatus) || text.none} />
            <Row label={text.blockers} value={value.reasonCodes.join(', ') || text.none} />
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

function formatMap(value: Record<string, string>): string {
  return Object.entries(value)
    .map(([key, status]) => `${key}: ${status}`)
    .join(', ');
}

function emptySnapshot(): MemorySemanticIndexSnapshot {
  return {
    status: 'available_disabled',
    enabled: false,
    runtimeInjectionEnabled: false,
    defaultBackend: 'in_memory_fixture',
    embeddingProfile: 'deterministic-fixture-v1',
    workspaceShardCount: 0,
    recordCount: 0,
    lastEvaluationStatus: 'missing',
    experimentalBackends: { turbovec: 'disabled' },
    backendStatus: { in_memory_fixture: 'disabled' },
    rawPersistence: false,
    reasonCodes: [],
  };
}
