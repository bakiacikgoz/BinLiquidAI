import type { UiLocale } from '../i18n';
import type { EnterpriseWorkspaceSnapshot } from './enterpriseWorkspaceTypes';

const copy = {
  en: {
    title: 'Agent enrollment',
    lead: 'Hash-only enrollment token, approval, and active fleet state.',
    active: 'Active',
    pending: 'Pending approval',
    revoked: 'Revoked',
    expired: 'Expired tokens',
    tokenAlert: 'Raw enrollment tokens are shown once only and are not persisted in snapshots.',
  },
  tr: {
    title: 'Agent enrollment',
    lead: 'Hash-only enrollment token, onay ve aktif filo durumu.',
    active: 'Aktif',
    pending: 'Bekleyen onay',
    revoked: 'Revoked',
    expired: 'Expired token',
    tokenAlert: 'Raw enrollment token sadece bir kez gosterilir ve snapshot icinde tutulmaz.',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function AgentEnrollmentView({
  snapshot,
  locale = 'en',
}: {
  snapshot?: EnterpriseWorkspaceSnapshot | null;
  locale?: UiLocale;
}) {
  const text = copy[locale];
  const enrollments = snapshot?.enrollments ?? { active: 0, pendingApproval: 0, revoked: 0, expiredTokens: 0 };

  return (
    <section className="workspace" data-testid="page-primary-region">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">{text.title}</p>
          <h2>{text.title}</h2>
          <p className="workspace-lead">{text.lead}</p>
        </div>
      </div>
      <div className="section-grid" data-testid="agent-enrollment">
        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.active}</h3>
              <p>{text.pending}: {enrollments.pendingApproval}</p>
            </div>
          </div>
          <p className="workspace-lead" role="alert">{text.tokenAlert}</p>
          <dl className="metric-list">
            <Row label={text.active} value={String(enrollments.active)} />
            <Row label={text.pending} value={String(enrollments.pendingApproval)} />
            <Row label={text.revoked} value={String(enrollments.revoked)} />
            <Row label={text.expired} value={String(enrollments.expiredTokens)} />
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
