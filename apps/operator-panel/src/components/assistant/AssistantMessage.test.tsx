import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

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

function renderMessage(turn: AssistantTurn) {
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
});
