import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { AssistantTurn } from '../../assistant/assistantTypes';
import { renderOperatorPanel } from '../../test/render';
import { AssistantMessage } from './AssistantMessage';

const noop = () => undefined;

function turnWithText(userText: string, assistantText: string): AssistantTurn {
  return {
    id: 'turn-1',
    startedAtUtc: '2026-03-08T09:20:00Z',
    completedAtUtc: '2026-03-08T09:20:05Z',
    composerControls: null,
    status: 'completed',
    eventSequence: 3,
    userMessage: {
      id: 'turn-1-user',
      text: userText,
      createdAtUtc: '2026-03-08T09:20:00Z',
    },
    assistantMessage: {
      id: 'turn-1-assistant',
      text: assistantText,
      findings: [],
      timeline: [],
      proposedAction: null,
      approval: null,
      referencedRuns: [],
      referencedArtifacts: [],
      metrics: null,
      warning: null,
      error: null,
    },
  };
}

function renderMessage(turn: AssistantTurn, onSubmitTask = noop) {
  return renderOperatorPanel(
    <AssistantMessage
      turn={turn}
      approvalDisabled={false}
      approvalDisabledReason=""
      emptyRunLabel="No run"
      debugRawEnabled={false}
      onReviewApproval={noop}
      onApprove={noop}
      onReject={noop}
      onExecute={noop}
      onRegenerate={noop}
      onSubmitTask={onSubmitTask}
    />,
  );
}

describe('AssistantMessage', () => {
  it('renders structured assistant markdown', () => {
    renderMessage(
      turnWithText(
        'Prepare a plan.',
        [
          '## Plan',
          '- Inspect `status.json`',
          '- Open [docs](https://example.com)',
          '',
          '| Step | State |',
          '| --- | --- |',
          '| Build | Pass |',
          '',
          '```ts',
          'const status = "pass";',
          '```',
        ].join('\n'),
      ),
    );

    expect(screen.getByRole('heading', { name: 'Plan' })).toBeInTheDocument();
    expect(screen.getByText('Inspect')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'docs' })).toHaveAttribute('href', 'https://example.com');
    expect(screen.getByRole('columnheader', { name: 'Step' })).toBeInTheDocument();
    expect(screen.getByText('const status = "pass";')).toBeInTheDocument();
  });

  it('collapses very long user messages without hiding the assistant response', async () => {
    const longUserText = Array(40).fill('Long diagnostic context with logs and repeated failure details.').join(' ');
    const { user } = renderMessage(turnWithText(longUserText, 'Short answer.'));

    expect(screen.getByRole('button', { name: 'Show more' })).toBeInTheDocument();
    expect(screen.getByText('Short answer.')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Show more' }));

    expect(screen.getByRole('button', { name: 'Collapse' })).toBeInTheDocument();
  });

  it('does not render operational timeline chips in the chat message', () => {
    const turn = turnWithText('Write a function.', 'Here is the function.');
    turn.assistantMessage.timeline = [
      {
        id: 'event-1',
        tone: 'warning',
        title: 'policy decision',
        subtitle: 'Approval required',
        timestampUtc: '2026-03-08T09:20:01Z',
      },
      {
        id: 'event-2',
        tone: 'info',
        title: 'Status',
        subtitle: 'Streaming response',
        timestampUtc: '2026-03-08T09:20:02Z',
      },
    ];

    renderMessage(turn);

    expect(screen.getByText('Here is the function.')).toBeInTheDocument();
    expect(screen.queryByText('policy decision')).not.toBeInTheDocument();
    expect(screen.queryByText('Approval required')).not.toBeInTheDocument();
    expect(screen.queryByText('Status')).not.toBeInTheDocument();
    expect(screen.queryByText('Streaming response')).not.toBeInTheDocument();
  });

  it('renders governed task proposal and submits with the plan hash', async () => {
    const onSubmitTask = vi.fn();
    const turn = turnWithText('Plan a task.', '');
    turn.assistantMessage.taskPlan = {
      schemaVersion: 'assistant-tasking.plan/v1',
      proposalId: 'astp-card',
      planHash: 'sha256:99719f8157f65dbb65e653d28c371889ed9e81cbb843b6f24700d31e2b023944',
      status: 'planned',
      intentKind: 'plan_agent_task',
      selectedAgent: null,
      candidateAgents: [],
      taskSummary: 'Read external ticket queue',
      riskClass: 'read_only',
      policyPreview: {
        decision: 'allow',
        riskClass: 'read_only',
        approvalRequired: false,
        safeToSubmit: true,
        reasonCode: 'ASSISTANT_TASK_READ_ONLY_ALLOWED',
        blockedReasons: [],
      },
      approvalRequired: false,
      submitMode: 'proposal_first',
      idempotencyKey: 'assistant-task:astp-card',
      evidenceExpectation: { mode: 'hash_only_redacted', expectedRefs: [], rawContentPersisted: false },
      safeToSubmit: true,
      blockedReasons: [],
      sourceRefs: ['docs/ASSISTANT_GOVERNED_TASKING.md'],
      createdAtUtc: '2026-03-08T09:00:00Z',
    };
    turn.assistantMessage.taskSubmission = {
      schemaVersion: 'assistant-tasking.submission/v1',
      proposalId: 'astp-card',
      planHash: turn.assistantMessage.taskPlan.planHash,
      status: 'accepted',
      policyDecision: 'allow',
      reasonCode: 'ASSISTANT_TASK_READ_ONLY_ALLOWED',
      runId: 'agt-card',
      approvalId: null,
      evidenceRef: null,
      replayStatus: null,
      idempotencyStatus: 'created',
      blockedReasons: [],
      nextActions: ['run.status'],
      generatedAtUtc: '2026-03-08T09:00:01Z',
    };

    const { user } = renderMessage(turn, onSubmitTask);

    expect(screen.getByText('Governed task proposal')).toBeInTheDocument();
    expect(screen.getByText('Read external ticket queue')).toBeInTheDocument();
    expect(screen.getByText('Task submission')).toBeInTheDocument();
    expect(screen.getByText('agt-card')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Submit with plan hash' }));

    const taskPlan = turn.assistantMessage.taskPlan;
    expect(taskPlan).not.toBeNull();
    expect(onSubmitTask).toHaveBeenCalledWith('astp-card', taskPlan?.planHash);
  });
});
