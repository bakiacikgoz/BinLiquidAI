import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

const workspace = vi.hoisted(() => ({ listMessages: vi.fn() }));

vi.mock('../adapters/productWorkspaceClient', () => ({ productWorkspaceClient: workspace }));

import { getAssistantFixture } from '../../assistant/assistantFixtures';
import { renderOperatorPanel } from '../../test/render';
import { ProductConversationView } from './ProductConversationView';

describe('ProductConversationView artifacts', () => {
  it('opens an assistant-produced artifact in the governed workspace', async () => {
    workspace.listMessages.mockResolvedValue({ messages: [] });
    const state = getAssistantFixture('running');
    state.referencedArtifacts = [{
      name: 'Release plan', artifactId: 'artifact-release-plan', revisionId: 'revision-1', kind: 'document',
      openable: true, summary: 'Governed release document',
    }];
    const onOpenArtifacts = vi.fn();
    const { user } = renderOperatorPanel(<ProductConversationView state={state} taskId="task-1" onOpenArtifacts={onOpenArtifacts} />);

    await user.click(await screen.findByRole('button', { name: 'Open in workspace' }));

    expect(onOpenArtifacts).toHaveBeenCalledWith('artifact-release-plan');
  });

  it('routes a governed assistant approval to its canonical detail', async () => {
    workspace.listMessages.mockResolvedValue({ messages: [] });
    const state = getAssistantFixture('running');
    state.turns[0].assistantMessage.approval = {
      approvalId: 'approval-release', title: 'Release', status: 'pending', risk: 'medium', detailLoaded: false,
    };
    const onOpenApproval = vi.fn();
    const { user } = renderOperatorPanel(<ProductConversationView state={state} taskId="task-1" onOpenApproval={onOpenApproval} />);

    await user.click(await screen.findByRole('button', { name: 'Open approval' }));

    expect(onOpenApproval).toHaveBeenCalledWith('approval-release');
    expect(screen.getByRole('button', { name: 'Feedback unavailable' })).toHaveAttribute(
      'data-disabled-reason',
      'ASSISTANT_FEEDBACK_CAPABILITY_UNAVAILABLE',
    );
  });
});
