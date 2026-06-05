import type {
  CodeIntelligenceSummary,
  DesignPartnerBetaStatus,
  PilotOperationsChecklistItem,
  PilotOperationsStatus,
} from '../../control-plane/types';

export interface DesignPartnerBetaReadinessLabels {
  title: string;
  status: string;
  codeIntelligence: string;
  pilotOperations: string;
  feedbackBundle: string;
  fallowTelemetry: string;
  secretScan: string;
  externalAgentGateway: string;
  ciInventory: string;
  claimBoundary: string;
  nextActions: string;
  blockers: string;
  warnings: string;
  baselineDebt: string;
  ready: string;
  missing: string;
  none: string;
}

const defaultLabels: DesignPartnerBetaReadinessLabels = {
  title: 'Beta Operations',
  status: 'Status',
  codeIntelligence: 'Code intelligence',
  pilotOperations: 'Pilot operations',
  feedbackBundle: 'Feedback bundle',
  fallowTelemetry: 'Fallow telemetry',
  secretScan: 'Secret scan',
  externalAgentGateway: 'External Agent Gateway v1.1',
  ciInventory: 'CI Node inventory',
  claimBoundary: 'Claim boundary',
  nextActions: 'Next actions',
  blockers: 'Blockers',
  warnings: 'Warnings',
  baselineDebt: 'Baseline debt',
  ready: 'ready',
  missing: 'missing',
  none: 'none',
};

export function DesignPartnerBetaReadinessCard({
  codeIntelligence,
  pilotOperations,
  designPartnerBeta,
  labels = defaultLabels,
}: {
  codeIntelligence?: CodeIntelligenceSummary | null;
  pilotOperations?: PilotOperationsStatus | null;
  designPartnerBeta?: DesignPartnerBetaStatus | null;
  labels?: Partial<DesignPartnerBetaReadinessLabels>;
}) {
  const copy = resolveLabels(labels);
  const model = buildBetaReadinessModel({
    codeIntelligence,
    pilotOperations,
    designPartnerBeta,
    labels: copy,
  });

  return (
    <article className="page-card">
      <h3>{copy.title}</h3>
      <dl className="metric-list">
        {model.metrics.map((metric) => (
          <MetricRow key={metric.label} label={metric.label} value={metric.value} />
        ))}
      </dl>

      <section className="run-list" aria-label={copy.nextActions}>
        <ReadinessItems
          title={copy.blockers}
          items={model.blockers}
          emptyLabel={copy.none}
          itemPrefix="blocker"
        />
        <ReadinessItems
          title={copy.warnings}
          items={model.warnings}
          emptyLabel={copy.none}
          itemPrefix="warning"
        />
        <ReadinessItems
          title={copy.nextActions}
          items={model.nextActions}
          emptyLabel={copy.none}
          itemPrefix="next-action"
        />
        <ReadinessItems
          title={copy.baselineDebt}
          items={model.baselineDebt}
          emptyLabel={copy.none}
          itemPrefix="baseline"
        />
      </section>
    </article>
  );
}

function resolveLabels(
  labels: Partial<DesignPartnerBetaReadinessLabels>,
): DesignPartnerBetaReadinessLabels {
  return { ...defaultLabels, ...labels };
}

function buildBetaReadinessModel({
  codeIntelligence,
  pilotOperations,
  designPartnerBeta,
  labels,
}: {
  codeIntelligence?: CodeIntelligenceSummary | null;
  pilotOperations?: PilotOperationsStatus | null;
  designPartnerBeta?: DesignPartnerBetaStatus | null;
  labels: DesignPartnerBetaReadinessLabels;
}) {
  const checks = checkMap(designPartnerBeta);
  return {
    metrics: betaMetrics({ codeIntelligence, pilotOperations, designPartnerBeta, checks, labels }),
    blockers: listOrEmpty(designPartnerBeta?.blockers),
    warnings: listOrEmpty(designPartnerBeta?.warnings),
    nextActions: nextActionLabels(pilotOperations),
    baselineDebt: baselineDebtLabels(codeIntelligence),
  };
}

function betaMetrics({
  codeIntelligence,
  pilotOperations,
  designPartnerBeta,
  checks,
  labels,
}: {
  codeIntelligence?: CodeIntelligenceSummary | null;
  pilotOperations?: PilotOperationsStatus | null;
  designPartnerBeta?: DesignPartnerBetaStatus | null;
  checks: Map<string, PilotOperationsChecklistItem>;
  labels: DesignPartnerBetaReadinessLabels;
}) {
  return [
    { label: labels.status, value: statusValue(designPartnerBeta?.status, labels.missing) },
    { label: labels.codeIntelligence, value: codeIntelligenceStatus(codeIntelligence, labels.missing) },
    { label: labels.pilotOperations, value: statusValue(pilotOperations?.status, labels.missing) },
    { label: labels.feedbackBundle, value: feedbackStatus(pilotOperations, labels) },
    { label: labels.externalAgentGateway, value: checkStatus(checks.get('external-agent-v1-1'), labels.missing) },
    { label: labels.ciInventory, value: checkStatus(checks.get('ci-node24-inventory'), labels.missing) },
    { label: labels.claimBoundary, value: checkStatus(checks.get('safety-claims'), labels.missing) },
    { label: labels.fallowTelemetry, value: telemetryStatus(codeIntelligence, labels.missing) },
    { label: labels.secretScan, value: statusValue(codeIntelligence?.secretScanStatus, labels.missing) },
  ];
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-row">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function ReadinessItems({
  title,
  items,
  emptyLabel,
  itemPrefix,
}: {
  title: string;
  items: string[];
  emptyLabel: string;
  itemPrefix: string;
}) {
  return (
    <article className="run-list-item">
      <strong>{title}</strong>
      {items.length ? (
        <ul>
          {items.map((item) => (
            <li key={`${itemPrefix}-${item}`}>{item}</li>
          ))}
        </ul>
      ) : (
        <span>{emptyLabel}</span>
      )}
    </article>
  );
}

function checkStatus(check: PilotOperationsChecklistItem | undefined, fallback: string): string {
  if (!check) {
    return fallback;
  }
  return check.detail ? `${check.status} (${check.detail})` : check.status;
}

function codeIntelligenceStatus(
  codeIntelligence: CodeIntelligenceSummary | null | undefined,
  fallback: string,
): string {
  return codeIntelligence ? `${codeIntelligence.status} / ${codeIntelligence.verdict}` : fallback;
}

function statusValue(value: string | null | undefined, fallback: string): string {
  return value ?? fallback;
}

function feedbackStatus(
  pilotOperations: PilotOperationsStatus | null | undefined,
  labels: DesignPartnerBetaReadinessLabels,
): string {
  return pilotOperations?.feedbackBundlePath ? labels.ready : labels.missing;
}

function telemetryStatus(
  codeIntelligence: CodeIntelligenceSummary | null | undefined,
  fallback: string,
): string {
  return codeIntelligence?.telemetryDisabled ? 'off' : fallback;
}

function checkMap(
  designPartnerBeta: DesignPartnerBetaStatus | null | undefined,
): Map<string, PilotOperationsChecklistItem> {
  return new Map((designPartnerBeta?.checks ?? []).map((check) => [check.itemId, check]));
}

function listOrEmpty(items: string[] | null | undefined): string[] {
  return items ?? [];
}

function nextActionLabels(pilotOperations: PilotOperationsStatus | null | undefined): string[] {
  return (pilotOperations?.nextActions ?? []).map((action) => `${action.severity}: ${action.label}`);
}

function baselineDebtLabels(codeIntelligence: CodeIntelligenceSummary | null | undefined): string[] {
  return (codeIntelligence?.buckets ?? [])
    .filter((bucket) => bucket.count > 0)
    .map((bucket) => `${bucket.label}: ${bucket.count}`);
}
