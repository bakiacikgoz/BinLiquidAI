import { describe, expect, it } from 'vitest';

import { createAssistantSession } from './assistantMappers';
import { buildAssistantPrompt } from './assistantPromptBuilder';

describe('assistant prompt builder', () => {
  it('builds a prompt without selected run context', () => {
    const result = buildAssistantPrompt({
      userMessage: 'hello',
      session: createAssistantSession('session-test'),
      selectedRunStatus: null,
      selectedRunEvents: [],
      selectedArtifacts: {},
      pendingApproval: null,
      systemHealth: null,
    });

    expect(result.compiledPrompt).toContain('## User message');
    expect(result.compiledPrompt).toContain('hello');
    expect(result.compiledPrompt).toContain('untrusted context');
  });

  it('redacts obvious secrets before compiling context', () => {
    const result = buildAssistantPrompt({
      userMessage: 'inspect sk-abc1234567890000',
      session: createAssistantSession('session-test'),
      selectedRunStatus: { token: 'ghp_abcdefghijklmnopqrstuvwxyz' },
      selectedRunEvents: [],
      selectedArtifacts: {},
      pendingApproval: null,
      systemHealth: null,
    });

    expect(result.compiledPrompt).not.toContain('sk-abc1234567890000');
    expect(result.compiledPrompt).not.toContain('ghp_abcdefghijklmnopqrstuvwxyz');
    expect(result.compiledPrompt).toContain('[redacted-secret]');
  });

  it('honors compiled prompt character limits', () => {
    const result = buildAssistantPrompt({
      userMessage: 'x'.repeat(1000),
      session: createAssistantSession('session-test'),
      selectedRunStatus: { big: 'y'.repeat(1000) },
      selectedRunEvents: [{ event: 'one', payload: 'z'.repeat(1000) }],
      selectedArtifacts: { 'status.json': { big: 'a'.repeat(1000) } },
      pendingApproval: null,
      systemHealth: null,
      maxChars: 500,
    });

    expect(result.characterCount).toBeLessThanOrEqual(500);
    expect(result.truncated).toBe(true);
    expect(result.omittedSections).toContain('compiledPromptTail');
  });

  it('only includes selected safe context attachments and tool intents', () => {
    const result = buildAssistantPrompt({
      userMessage: 'explain blocker',
      session: createAssistantSession('session-test'),
      selectedRunStatus: { run_id: 'run-test' },
      selectedRunEvents: [{ event: 'approval_required' }],
      selectedArtifacts: { 'status.json': { status: 'blocked' } },
      pendingApproval: { approval_id: 'apr-test' },
      systemHealth: { health: 'Healthy' },
      controls: {
        contextAttachmentKinds: ['active_run', 'approval_summary'],
        toolIntents: ['explain_policy_blocker'],
      },
    });

    expect(result.compiledPrompt).toContain('## Allowed tool intents');
    expect(result.compiledPrompt).toContain('explain_policy_blocker');
    expect(result.compiledPrompt).toContain('## Selected run status');
    expect(result.compiledPrompt).toContain('## Pending approval');
    expect(result.compiledPrompt).not.toContain('## Recent normalized events');
    expect(result.compiledPrompt).not.toContain('## Artifact summary');
    expect(result.compiledPrompt).not.toContain('## System health');
  });
});
