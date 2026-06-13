import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { ProviderTrustSurface } from './ProviderTrustSurface';
import type { ProviderGovernanceSnapshot, ProviderRuntimeSnapshot } from '../../control-plane/types';

describe('ProviderTrustSurface', () => {
  it('renders provider trust badges without raw secrets or raw JSON', () => {
    const snapshot: ProviderGovernanceSnapshot = {
      contractVersion: 'control-plane.provider-governance/v1',
      generatedAtUtc: '2026-06-13T12:00:00.000Z',
      overallStatus: 'conditional',
      blockingReasons: ['blocked_external_credentials'],
      providers: [
        {
          providerKind: 'openai_responses',
          displayName: 'OpenAI Responses Native Preview',
          status: 'blocked',
          credentialState: 'missing',
          canaryOnly: true,
          supportsStreaming: true,
          serverToolsPolicy: 'denied',
          customToolsPolicy: 'proposal_only',
          retentionPolicy: 'hash_only_store_false',
          lastConformanceStatus: 'pass',
          blockingReasons: ['blocked_external_credentials'],
        },
        {
          providerKind: 'anthropic_messages',
          displayName: 'Anthropic Claude Messages Native Preview',
          status: 'canary_only',
          credentialState: 'redacted',
          canaryOnly: true,
          supportsStreaming: true,
          serverToolsPolicy: 'denied',
          customToolsPolicy: 'proposal_only',
          retentionPolicy: 'hash_only_store_false',
          lastConformanceStatus: 'pass',
          blockingReasons: [],
        },
      ],
    };
    const runtime: ProviderRuntimeSnapshot = {
      contractVersion: 'control-plane.provider-runtime/v1',
      generatedAtUtc: '2026-06-13T12:00:00.000Z',
      enabled: true,
      latestInvocations: [
        {
          schemaVersion: 'provider.invocation.v1',
          status: 'pass',
          invocationId: 'provider-inv-1234',
          providerKind: 'openai_responses',
          model: 'gpt-placeholder',
          runtimeMode: 'dry_run',
          policyDecision: {
            decision: 'allow',
            reasonCodes: ['PROVIDER_POLICY_PASS'],
          },
          requestHash: 'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
          responseHash: 'sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
          rawPersistence: false,
          evidenceMode: 'hash_only',
          toolPolicy: {
            serverToolsPolicy: 'denied',
            customToolsPolicy: 'proposal_only',
            requestedServerTools: [],
          },
          blockingReasons: [],
          createdAtUtc: '2026-06-13T12:00:00.000Z',
        },
      ],
      workflowProofs: [
        {
          schemaVersion: 'provider.workflow-proof.v1',
          status: 'pass',
          workflowId: 'read-only-ops-triage',
          workflowKind: 'read_only_ops_triage',
          agentId: 'provider-governed-ops',
          providerInvocations: ['provider-inv-1234'],
          proposals: [
            {
              proposalId: 'proposal-restart-service',
              actionId: 'restart-service',
              riskClass: 'mutation',
              executionMode: 'proposal_only',
              effectSummary: 'restart service is approval-gated',
            },
          ],
          executedMutations: 0,
          approvalTicketsCreated: 1,
          evidenceArtifacts: ['artifacts/provider-runtime/invocations/provider-inv-1234.json'],
          blockingReasons: [],
          generatedAtUtc: '2026-06-13T12:00:00.000Z',
        },
      ],
      blockingReasons: [],
    };

    const html = renderToStaticMarkup(
      <ProviderTrustSurface snapshot={snapshot} runtime={runtime} locale="en" />,
    );

    expect(html).toContain('Provider Trust');
    expect(html).toContain('Provider Execution Evidence');
    expect(html).toContain('dry_run');
    expect(html).toContain('raw_persistence_off');
    expect(html).toContain('Workflow Proof');
    expect(html).toContain('executed_mutations=0');
    expect(html).toContain('OpenAI Responses Native Preview');
    expect(html).toContain('Anthropic Claude Messages Native Preview');
    expect(html).toContain('canary_only');
    expect(html).toContain('hash_only');
    expect(html).toContain('server_tools_denied');
    expect(html).toContain('proposal_only');
    expect(html).toContain('credential_missing');
    expect(html).not.toContain('sk-');
    expect(html).not.toContain('{&quot;');
  });
});
