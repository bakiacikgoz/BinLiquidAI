import type { UiLocale } from '../i18n';
import { mapEnterpriseWorkspace } from './enterpriseWorkspaceMappers';
import type { EnterpriseWorkspaceSnapshot } from './enterpriseWorkspaceTypes';

const copy = {
  en: {
    kicker: 'Enterprise workspace',
    title: 'Workspace onboarding',
    lead: 'Self-hosted organization setup, signed identity health, agent enrollment, and device fleet status.',
    identity: 'Identity',
    workspaces: 'Workspaces',
    principals: 'Principals',
    memberships: 'Memberships',
    activeAgents: 'Active agents',
    pending: 'Pending approvals',
    devices: 'Devices',
    network: 'Network listener',
    blockers: 'Blocking reasons',
    none: 'none',
  },
  tr: {
    kicker: 'Enterprise workspace',
    title: 'Workspace onboarding',
    lead: 'Self-hosted organizasyon kurulumu, signed identity sagligi, agent enrollment ve cihaz filosu durumu.',
    identity: 'Identity',
    workspaces: 'Workspace',
    principals: 'Principal',
    memberships: 'Membership',
    activeAgents: 'Aktif agent',
    pending: 'Bekleyen onay',
    devices: 'Cihaz',
    network: 'Network listener',
    blockers: 'Bloklayicilar',
    none: 'yok',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function EnterpriseWorkspaceOverview({
  snapshot,
  locale = 'en',
}: {
  snapshot?: EnterpriseWorkspaceSnapshot | null;
  locale?: UiLocale;
}) {
  const summary = mapEnterpriseWorkspace(snapshot);
  const text = copy[locale];
  const blockers = summary.blockingReasons.length ? summary.blockingReasons.join(', ') : text.none;

  return (
    <section className="workspace" data-testid="page-primary-region">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">{text.kicker}</p>
          <h2>{text.title}</h2>
          <p className="workspace-lead">{text.lead}</p>
        </div>
      </div>

      <div className="section-grid" data-testid="enterprise-workspace">
        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{summary.organizationName}</h3>
              <p>{summary.status}</p>
            </div>
          </div>
          <dl className="metric-list">
            <Row label={text.identity} value={summary.identityStatus} />
            <Row label={text.workspaces} value={String(summary.workspaceCount)} />
            <Row label={text.network} value={summary.networkListenerLabel} />
          </dl>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.activeAgents}</h3>
              <p>{text.pending}: {summary.pendingApprovalCount}</p>
            </div>
          </div>
          <dl className="metric-list">
            <Row label={text.principals} value={String(summary.principalCount)} />
            <Row label={text.memberships} value={String(summary.membershipCount)} />
            <Row label={text.devices} value={String(summary.deviceCount)} />
            <Row label={text.activeAgents} value={String(summary.activeAgentCount)} />
          </dl>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.blockers}</h3>
              <p>{blockers}</p>
            </div>
          </div>
          <div className="reason-list" aria-label={text.blockers}>
            {summary.blockingReasons.length ? (
              summary.blockingReasons.map((reason) => (
                <span className="reason-chip" data-tone="warn" key={reason}>
                  {reason}
                </span>
              ))
            ) : (
              <span className="reason-chip" data-tone="ok">{text.none}</span>
            )}
          </div>
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
