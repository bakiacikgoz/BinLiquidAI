import type { GovernedPilotWorkflowSnapshot } from '../control-plane/types';
import type { UiLocale } from '../i18n';

const copy = {
  en: {
    title: 'Governed Pilot Workflow',
    lead: 'Deterministic pilot closure proof across governed memory, provider dry-run, approvals, and hash-only evidence.',
    status: 'Status',
    workflow: 'Workflow',
    run: 'Run',
    mode: 'Mode',
    evidence: 'Evidence',
    rawPersistence: 'Raw persistence',
    claimGuard: 'Claim guard',
    verifier: 'Verifier',
    blockedClaims: 'Blocked claims',
    report: 'Report',
    summary: 'Summary',
    blockers: 'Blockers',
    warnings: 'Warnings',
    none: 'none',
    missing: 'not run',
  },
  tr: {
    title: 'Governed Pilot Workflow',
    lead: 'Governed memory, provider dry-run, onaylar ve hash-only evidence için deterministik pilot kapanış kanıtı.',
    status: 'Durum',
    workflow: 'Workflow',
    run: 'Run',
    mode: 'Mod',
    evidence: 'Evidence',
    rawPersistence: 'Raw persistence',
    claimGuard: 'Claim guard',
    verifier: 'Verifier',
    blockedClaims: 'Bloke claimler',
    report: 'Rapor',
    summary: 'Özet',
    blockers: 'Bloklayıcılar',
    warnings: 'Uyarılar',
    none: 'yok',
    missing: 'çalışmadı',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function GovernedPilotWorkflowView({
  snapshot,
  locale = 'en',
}: {
  snapshot?: GovernedPilotWorkflowSnapshot | null;
  locale?: UiLocale;
}) {
  const text = copy[locale];
  const blockedClaims = snapshot?.blockedClaims ?? [];
  const blockers = snapshot?.blockingReasons ?? [];
  const warnings = snapshot?.warnings ?? [];
  return (
    <section className="workspace" data-testid="page-primary-region">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">{text.evidence}</p>
          <h2>{text.title}</h2>
          <p className="workspace-lead">{text.lead}</p>
        </div>
      </div>
      <div className="section-grid" data-testid="governed-pilot-workflow">
        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.status}</h3>
              <p>{snapshot?.enabled ? snapshot.status : text.missing}</p>
            </div>
          </div>
          <dl className="metric-list">
            <Row label={text.workflow} value={snapshot?.workflowId ?? text.none} />
            <Row label={text.run} value={snapshot?.runId ?? text.none} />
            <Row label={text.mode} value={snapshot?.mode ?? text.none} />
            <Row label={text.evidence} value={snapshot?.evidenceMode ?? 'hash_only'} />
            <Row label={text.rawPersistence} value={String(snapshot?.rawPersistence ?? false)} />
            <Row label={text.claimGuard} value={snapshot?.claimGuardStatus ?? text.missing} />
            <Row label={text.verifier} value={snapshot?.verifierStatus ?? 'missing'} />
          </dl>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.blockedClaims}</h3>
              <p>{blockedClaims.length > 0 ? `${blockedClaims.length}` : text.none}</p>
            </div>
          </div>
          <ul className="compact-list">
            {blockedClaims.length > 0 ? blockedClaims.map((claim) => <li key={claim}>{claim}</li>) : <li>{text.none}</li>}
          </ul>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>{text.report}</h3>
              <p>{snapshot?.latestReportPath ?? text.none}</p>
            </div>
          </div>
          <dl className="metric-list">
            <Row label={text.summary} value={snapshot?.latestSummaryPath ?? text.none} />
            <Row label={text.blockers} value={blockers.join(', ') || text.none} />
            <Row label={text.warnings} value={warnings.join(', ') || text.none} />
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
