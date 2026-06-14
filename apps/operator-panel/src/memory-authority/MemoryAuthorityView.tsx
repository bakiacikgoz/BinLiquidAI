import type { UiLocale } from '../i18n';
import type { WorkspaceMemoryAuthorityHealth } from '../control-plane/types';

const copy = {
  en: {
    kicker: 'Workspace Memory',
    title: 'Memory Authority',
    lead: 'Workspace-scoped authority status, RBAC posture, and sync blockers without raw memory exposure.',
    authority: 'Authority',
    counts: 'Counts',
    status: 'Status',
    mode: 'Mode',
    raw: 'Raw content',
    network: 'Network listener',
    workspaces: 'Workspaces',
    principals: 'Principals',
    scopes: 'Active scopes',
    proposals: 'Pending proposals',
    conflicts: 'Pending conflicts',
    blockers: 'Blockers',
    none: 'none',
    exposed: 'exposed',
    blocked: 'blocked',
    disabled: 'disabled',
  },
  tr: {
    kicker: 'Workspace Memory',
    title: 'Memory Authority',
    lead: 'Ham memory göstermeden workspace authority, RBAC ve sync engel durumları.',
    authority: 'Authority',
    counts: 'Sayımlar',
    status: 'Durum',
    mode: 'Mod',
    raw: 'Raw içerik',
    network: 'Network listener',
    workspaces: 'Workspace',
    principals: 'Principal',
    scopes: 'Aktif scope',
    proposals: 'Bekleyen proposal',
    conflicts: 'Bekleyen conflict',
    blockers: 'Engeller',
    none: 'yok',
    exposed: 'açık',
    blocked: 'kapalı',
    disabled: 'disabled',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function MemoryAuthorityView({
  authority,
  locale = 'en',
}: {
  authority?: WorkspaceMemoryAuthorityHealth | null;
  locale?: UiLocale;
}) {
  const text = copy[locale];
  const snapshot = authority ?? emptyAuthority();
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
        <article className="page-card" data-testid="memory-authority-status">
          <div className="page-card-header">
            <div>
              <h3>{text.authority}</h3>
              <p>{snapshot.status}</p>
            </div>
          </div>
          <dl className="metric-list">
            <Row label={text.status} value={snapshot.status} />
            <Row label={text.mode} value={snapshot.mode} />
            <Row label={text.raw} value={snapshot.rawContentExposed ? text.exposed : text.blocked} />
            <Row label={text.network} value={snapshot.networkListenerEnabled ? text.exposed : text.blocked} />
            <Row label={text.blockers} value={snapshot.blockingReasons.join(', ') || text.none} />
          </dl>
        </article>

        <article className="page-card" data-testid="memory-authority-counts">
          <div className="page-card-header">
            <div>
              <h3>{text.counts}</h3>
              <p>{snapshot.lastSyncPackStatus ?? text.none}</p>
            </div>
          </div>
          <dl className="metric-list">
            <Row label={text.workspaces} value={String(snapshot.workspaceCount)} />
            <Row label={text.principals} value={String(snapshot.principalCount)} />
            <Row label={text.scopes} value={String(snapshot.activeScopeCount)} />
            <Row label={text.proposals} value={String(snapshot.pendingProposalCount)} />
            <Row label={text.conflicts} value={String(snapshot.pendingConflictCount)} />
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

function emptyAuthority(): WorkspaceMemoryAuthorityHealth {
  return {
    status: 'disabled',
    mode: 'local_authority',
    workspaceCount: 0,
    principalCount: 0,
    activeScopeCount: 0,
    pendingProposalCount: 0,
    pendingConflictCount: 0,
    lastSyncPackStatus: null,
    rawContentExposed: false,
    networkListenerEnabled: false,
    blockingReasons: [],
  };
}
