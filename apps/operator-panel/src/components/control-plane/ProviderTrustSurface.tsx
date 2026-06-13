import type { UiLocale } from '../../i18n';
import type {
  ProviderGovernanceSnapshot,
  ProviderInvocationArtifact,
  ProviderRegistryEntry,
  ProviderRuntimeSnapshot,
  ProviderWorkflowProofArtifact,
} from '../../control-plane/types';

const copy = {
  en: {
    title: 'Provider Trust',
    generated: 'generated',
    empty: 'No trusted provider available',
    status: 'status',
    credential: 'credential',
    conformance: 'conformance',
    executionTitle: 'Provider Execution Evidence',
    workflowTitle: 'Workflow Proof',
    emptyRuntime: 'No provider invocation evidence yet',
  },
  tr: {
    title: 'Provider Güveni',
    generated: 'üretilme',
    empty: 'Güvenilir provider yok',
    status: 'durum',
    credential: 'credential',
    conformance: 'conformance',
    executionTitle: 'Provider Yürütme Kanıtı',
    workflowTitle: 'Workflow Kanıtı',
    emptyRuntime: 'Henüz provider invocation kanıtı yok',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function ProviderTrustSurface({
  snapshot,
  runtime,
  locale = 'en',
}: {
  snapshot?: ProviderGovernanceSnapshot | null;
  runtime?: ProviderRuntimeSnapshot | null;
  locale?: UiLocale;
}) {
  const text = copy[locale];
  const providers = snapshot?.providers ?? [];
  const latestInvocation = runtime?.latestInvocations?.[0] ?? null;
  const latestWorkflow = runtime?.workflowProofs?.[0] ?? null;

  return (
    <article className="page-card provider-trust-surface">
      <div className="page-card-header">
        <div>
          <h3>{text.title}</h3>
          <p>
            {snapshot?.overallStatus ?? 'blocked'} · {text.generated}{' '}
            {snapshot?.generatedAtUtc ?? '-'}
          </p>
        </div>
      </div>
      {providers.length === 0 ? <p className="supporting">{text.empty}</p> : null}
      <div className="run-list">
        {providers.map((provider) => (
          <ProviderTrustRow key={provider.providerKind} provider={provider} text={text} />
        ))}
      </div>
      <ProviderExecutionEvidence invocation={latestInvocation} workflow={latestWorkflow} text={text} />
    </article>
  );
}

function ProviderTrustRow({
  provider,
  text,
}: {
  provider: ProviderRegistryEntry;
  text: (typeof copy)['en'];
}) {
  return (
    <article className="run-list-item provider-trust-row">
      <strong>{provider.displayName}</strong>
      <span>
        {text.status}: {provider.status}
      </span>
      <small>
        {text.credential}: {provider.credentialState} · {text.conformance}:{' '}
        {provider.lastConformanceStatus ?? 'unknown'}
      </small>
      <div className="reason-list" aria-label={`${provider.displayName} policy badges`}>
        {provider.canaryOnly ? <span className="reason-chip">canary_only</span> : null}
        <span className="reason-chip">hash_only</span>
        {provider.serverToolsPolicy === 'denied' ? (
          <span className="reason-chip">server_tools_denied</span>
        ) : null}
        {provider.customToolsPolicy === 'proposal_only' ? (
          <span className="reason-chip">proposal_only</span>
        ) : null}
        {provider.credentialState === 'missing' ? (
          <span className="reason-chip">credential_missing</span>
        ) : null}
      </div>
    </article>
  );
}

function ProviderExecutionEvidence({
  invocation,
  workflow,
  text,
}: {
  invocation: ProviderInvocationArtifact | null;
  workflow: ProviderWorkflowProofArtifact | null;
  text: (typeof copy)['en'];
}) {
  if (!invocation && !workflow) {
    return (
      <section className="run-list-item provider-execution-evidence">
        <strong>{text.executionTitle}</strong>
        <span>{text.emptyRuntime}</span>
      </section>
    );
  }
  return (
    <section className="run-list-item provider-execution-evidence">
      <strong>{text.executionTitle}</strong>
      {invocation ? (
        <>
          <span>
            {invocation.providerKind} · {invocation.runtimeMode} · {invocation.status}
          </span>
          <div className="reason-list" aria-label="Provider invocation evidence badges">
            <span className="reason-chip">{invocation.evidenceMode}</span>
            {!invocation.rawPersistence ? <span className="reason-chip">raw_persistence_off</span> : null}
            {invocation.toolPolicy.serverToolsPolicy === 'denied' ? (
              <span className="reason-chip">server_tools_denied</span>
            ) : null}
            {invocation.toolPolicy.customToolsPolicy === 'proposal_only' ? (
              <span className="reason-chip">proposal_only</span>
            ) : null}
          </div>
        </>
      ) : null}
      {workflow ? (
        <div className="provider-workflow-proof">
          <strong>{text.workflowTitle}</strong>
          <small>
            {workflow.workflowKind} · {workflow.status} · executed_mutations=
            {workflow.executedMutations}
          </small>
        </div>
      ) : null}
    </section>
  );
}
