import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { getAssistantFixture } from '../../assistant/assistantFixtures';
import { renderOperatorPanel } from '../../test/render';
import { AssistantWorkbench } from './AssistantWorkbench';

describe('AssistantWorkbench', () => {
  it('renders active assistant output and artifact previews', async () => {
    const onSelectArtifact = vi.fn();
    const { user } = renderOperatorPanel(
      <AssistantWorkbench
        state={getAssistantFixture('running')}
        artifacts={[
          { name: 'status.json', summary: 'blocked', value: { status: 'blocked', job_id: 'job-1' } },
          { name: 'tasks.json', summary: '2 tasks', value: { tasks: [{ id: 'task-1' }] } },
        ]}
        selectedArtifactName="status.json"
        onSelectArtifact={onSelectArtifact}
        onViewRuns={vi.fn()}
      />,
    );

    expect(screen.getByText('Workbench')).toBeInTheDocument();
    expect(screen.getByText('The selected run is blocked by an approval gate.')).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes('"status": "blocked"'))).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'tasks.json' }));

    expect(onSelectArtifact).toHaveBeenCalledWith('tasks.json');
  });
});
