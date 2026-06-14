import type { UiLocale } from '../i18n';
import type { MemoryPolicyEnforcementSnapshot } from '../control-plane/types';

const copy = {
  en: {
    title: 'Memory Policy Enforcement',
    lead: 'Fail-closed runtime memory decisions with hash-only evidence.',
    status: 'Status',
    semanticMode: 'Semantic mode',
    reads: 'Reads',
    writes: 'Writes',
    denied: 'Denied',
    approval: 'Approval required',
    degraded: 'Degraded',
    rawLeaks: 'Raw leaks',
    evidence: 'Evidence',
    reasons: 'Reasons',
    none: 'none',
  },
  tr: {
    title: 'Memory Policy Enforcement',
    lead: 'Hash-only evidence ile fail-closed runtime memory kararları.',
    status: 'Durum',
    semanticMode: 'Semantic modu',
    reads: 'Read',
    writes: 'Write',
    denied: 'Denied',
    approval: 'Onay gerekli',
    degraded: 'Degraded',
    rawLeaks: 'Raw leak',
    evidence: 'Evidence',
    reasons: 'Nedenler',
    none: 'yok',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function MemoryRuntimePolicyView({
  snapshot,
  locale = 'en',
}: {
  snapshot?: MemoryPolicyEnforcementSnapshot | null;
  locale?: UiLocale;
}) {
  const text = copy[locale];
  return (
    <article className="page-card" data-testid="memory-policy-enforcement">
      <div className="page-card-header">
        <div>
          <h3>{text.title}</h3>
          <p>{text.lead}</p>
        </div>
      </div>
      <dl className="metric-list">
        <Row label={text.status} value={snapshot?.status ?? 'disabled'} />
        <Row label={text.semanticMode} value={snapshot?.semanticRuntimeMode ?? 'disabled'} />
        <Row label={text.reads} value={String(snapshot?.readEventCount ?? 0)} />
        <Row label={text.writes} value={String(snapshot?.writeEventCount ?? 0)} />
        <Row label={text.denied} value={String(snapshot?.deniedCount ?? 0)} />
        <Row label={text.approval} value={String(snapshot?.approvalRequiredCount ?? 0)} />
        <Row label={text.degraded} value={String(snapshot?.degradedCount ?? 0)} />
        <Row label={text.rawLeaks} value={String(snapshot?.rawLeakCount ?? 0)} />
        <Row label={text.evidence} value={(snapshot?.latestEvidenceRefs ?? []).join(', ') || text.none} />
        <Row label={text.reasons} value={(snapshot?.reasonCodes ?? []).join(', ') || text.none} />
      </dl>
    </article>
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
