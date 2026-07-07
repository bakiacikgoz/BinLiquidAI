import { getTargetClaimBadge, mapLocalProductReadiness } from './localProductMappers';

export function LocalProductReadinessView({ report }: { report: unknown }) {
  const vm = mapLocalProductReadiness(report);
  const badge = getTargetClaimBadge(vm.currentTarget);

  return (
    <section className="workspace" data-testid="page-primary-region">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">Platform readiness</p>
          <h2>Local Product Readiness</h2>
          <p className="workspace-lead">
            Current machine evidence and platform claim boundaries for the local desktop product.
          </p>
        </div>
      </div>

      <div className="section-grid" data-testid="local-product-readiness">
        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>Current machine</h3>
              <p>{vm.currentTarget.targetId}</p>
            </div>
            <span className="reason-chip" data-tone={badge === 'supported' ? 'success' : 'warning'}>
              {badge}
            </span>
          </div>
          <dl className="metric-list">
            <Row label="OS" value={vm.currentTarget.os} />
            <Row label="Architecture" value={vm.currentTarget.arch} />
            <Row label="Status" value={vm.overallStatus} />
          </dl>
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>Supported claims</h3>
              <p>{vm.productClaimSummary}</p>
            </div>
          </div>
          <ChipList items={vm.supportedClaims} empty="none" tone="success" />
        </article>

        <article className="page-card">
          <div className="page-card-header">
            <div>
              <h3>Not evidenced targets</h3>
              <p>Targets listed here are not product-supported claims yet.</p>
            </div>
          </div>
          <ChipList items={vm.notEvidencedTargets} empty="none" tone="warning" />
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

function ChipList({
  items,
  empty,
  tone,
}: {
  items: string[];
  empty: string;
  tone: 'success' | 'warning' | 'error';
}) {
  if (items.length === 0) {
    return <p className="supporting">{empty}</p>;
  }
  return (
    <div className="reason-list">
      {items.map((item) => (
        <span className="reason-chip" data-tone={tone} key={item}>
          {item}
        </span>
      ))}
    </div>
  );
}

