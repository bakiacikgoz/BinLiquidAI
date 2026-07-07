import { describe, expect, it } from 'vitest';

import {
  normalizeAssistantKnowledgeSearchResponse,
  previewAssistantKnowledgeSearch,
} from './assistantSystemKnowledge';

describe('assistant system knowledge mappers', () => {
  it('normalizes bridge search responses', () => {
    const payload = normalizeAssistantKnowledgeSearchResponse({
      status: 'ready',
      intent: 'agent_task',
      hits: [{ path: 'docs/AI_ASSISTANT_SYSTEM_KNOWLEDGE.md', heading: 'Agent task', score: 0.9 }],
      context: {
        status: 'available',
        identityBrief: 'identity',
        answerRules: ['cite sources'],
        sources: [{ path: 'docs/AI_ASSISTANT_SYSTEM_KNOWLEDGE.md', heading: 'Agent task', score: 0.9 }],
        contextText: 'Source context',
        omittedSources: [],
        blockingReasons: [],
      },
      blockingReasons: [],
    });

    expect(payload.contractVersion).toBe('operator-panel.assistant-system-knowledge/v1');
    expect(payload.status).toBe('ready');
    expect(payload.context.status).toBe('available');
    expect(payload.context.sources[0]?.path).toBe('docs/AI_ASSISTANT_SYSTEM_KNOWLEDGE.md');
  });

  it('provides preview grounded sources', () => {
    const payload = previewAssistantKnowledgeSearch('AegisOS agent task');

    expect(payload.status).toBe('ready');
    expect(payload.intent).toBe('agent_task');
    expect(payload.context.sources[0]?.path).toBe('docs/AI_ASSISTANT_SYSTEM_KNOWLEDGE.md');
  });
});
