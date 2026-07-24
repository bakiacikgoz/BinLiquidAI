import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { renderOperatorPanel } from '../../test/render';
import { WorkSurface } from './WorkSurface';

describe('WorkSurface', () => {
  it('opens the governed artifact workspace through its owner callback', async () => {
    const onOpenArtifacts = vi.fn();
    const { user } = renderOperatorPanel(
      <WorkSurface taskTitle="Release checklist" onOpenArtifacts={onOpenArtifacts} />,
    );

    await user.click(screen.getByRole('button', { name: 'Open Artifact Workspace' }));

    expect(onOpenArtifacts).toHaveBeenCalledTimes(1);
  });
});
