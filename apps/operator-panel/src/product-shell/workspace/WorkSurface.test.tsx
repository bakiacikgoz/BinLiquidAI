import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../terminal/TerminalSurface', () => ({ TerminalSurface: () => null }));
vi.mock('../browser/BrowserSurface', () => ({ BrowserSurface: () => null }));
vi.mock('../browser/PreviewSurface', () => ({ PreviewSurface: () => null }));

import { renderOperatorPanel } from '../../test/render';
import { WorkSurface } from './WorkSurface';

describe('WorkSurface', () => {
  it('opens the governed artifact workspace through its owner callback', async () => {
    const onOpenArtifacts = vi.fn();
    const onOpenTerminal = vi.fn();
    const onOpenBrowser = vi.fn();
    const onOpenPreview = vi.fn();
    const { user } = renderOperatorPanel(
      <WorkSurface taskTitle="Release checklist" onOpenArtifacts={onOpenArtifacts} onOpenTerminal={onOpenTerminal} onOpenBrowser={onOpenBrowser} onOpenPreview={onOpenPreview} />,
    );

    await user.click(screen.getByRole('button', { name: 'Open Artifact Workspace' }));
    await user.click(screen.getByRole('button', { name: 'Open terminal' }));
    await user.click(screen.getByRole('button', { name: 'Open browser' }));
    await user.click(screen.getByRole('button', { name: 'Open preview' }));

    expect(onOpenArtifacts).toHaveBeenCalledTimes(1);
    expect(onOpenTerminal).toHaveBeenCalledTimes(1);
    expect(onOpenBrowser).toHaveBeenCalledTimes(1);
    expect(onOpenPreview).toHaveBeenCalledTimes(1);
  });
});
