import { describe, expect, it } from 'vitest';

import {
  normalizeAssistantTaskPlan,
  normalizeAssistantTaskSubmissionResult,
} from './assistantTaskingMappers';

describe('assistant tasking mappers', () => {
  it('normalizes governed task plan payloads with candidates and policy preview', () => {
    const plan = normalizeAssistantTaskPlan({
      proposalId: 'astp-normalized',
      planHash: 'sha256:99719f8157f65dbb65e653d28c371889ed9e81cbb843b6f24700d31e2b023944',
      status: 'planned',
      intentKind: 'plan_agent_task',
      candidateAgents: [
        {
          agentId: 'external-agent',
          label: 'External Agent',
          enrolled: true,
          workspaceId: 'pilot-workspace',
          allowedSurfaces: ['external_gateway'],
          declaredActions: ['read'],
          qualificationStatus: 'ready',
        },
      ],
      taskSummary: 'Read external queue',
      riskClass: 'read_only',
      policyPreview: {
        decision: 'allow',
        riskClass: 'read_only',
        approvalRequired: false,
        safeToSubmit: true,
        reasonCode: 'ASSISTANT_TASK_READ_ONLY_ALLOWED',
      },
      approvalRequired: false,
      submitMode: 'proposal_first',
      evidenceExpectation: { expectedRefs: ['artifact.json'] },
      safeToSubmit: true,
      sourceRefs: ['docs/ASSISTANT_GOVERNED_TASKING.md'],
      createdAtUtc: '2026-03-08T09:00:00Z',
    });

    expect(plan.schemaVersion).toBe('assistant-tasking.plan/v1');
    expect(plan.candidateAgents[0]?.agentId).toBe('external-agent');
    expect(plan.policyPreview.decision).toBe('allow');
    expect(plan.evidenceExpectation.rawContentPersisted).toBe(false);
  });

  it('normalizes denied submission payloads without raw body rendering fields', () => {
    const result = normalizeAssistantTaskSubmissionResult({
      proposalId: 'astp-denied',
      status: 'denied',
      policyDecision: 'deny',
      reasonCode: 'ASSISTANT_TASK_DESTRUCTIVE_DENIED',
      blockedReasons: ['ASSISTANT_TASK_DESTRUCTIVE_DENIED'],
      nextActions: ['revise.request'],
    });

    expect(result.status).toBe('denied');
    expect(result.policyDecision).toBe('deny');
    expect(result.blockedReasons).toContain('ASSISTANT_TASK_DESTRUCTIVE_DENIED');
    expect(Object.keys(result)).not.toContain('rawContent');
  });
});
