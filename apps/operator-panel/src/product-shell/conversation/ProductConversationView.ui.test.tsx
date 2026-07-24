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

    expect(onOpenArtifacts).toHaveBeenCalledTimes(1);
  });
});
