import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../terminal/TerminalSurface', () => ({ TerminalSurface: () => <div>Terminal surface</div> }));
vi.mock('../browser/BrowserSurface', () => ({ BrowserSurface: () => <div>Browser surface</div> }));
vi.mock('../browser/PreviewSurface', () => ({ PreviewSurface: () => <div>Preview surface</div> }));
vi.mock('./ProductArtifactWorkspace', () => ({ ProductArtifactWorkspace: () => <div>Artifact surface</div> }));

import { getAssistantFixture } from '../../assistant/assistantFixtures';
import { renderOperatorPanel } from '../../test/render';
import { WorkspaceTabs } from './WorkspaceTabs';
import { createWorkspaceTab } from './workspaceTabState';

describe('WorkspaceTabs', () => {
  it('uses unique runtime tab IDs and delegates activation and close lifecycle', async () => {
    const first = createWorkspaceTab('terminal');
    const second = createWorkspaceTab('terminal');
    const onActivate = vi.fn();
    const onClose = vi.fn();
    expect(first.id).not.toBe(second.id);

    const { user } = renderOperatorPanel(<WorkspaceTabs tabs={[first, second]} activeTabId={second.id} assistantState={getAssistantFixture('running')} onActivate={onActivate} onClose={onClose} />);

    expect(screen.getByText('Terminal surface')).toBeInTheDocument();
    await user.click(screen.getAllByRole('tab', { name: 'Terminal' })[0]);
    await user.click(screen.getAllByRole('button', { name: 'Close Terminal' })[1]);

    expect(onActivate).toHaveBeenCalledWith(first.id);
    expect(onClose).toHaveBeenCalledWith(second.id);
  });
});
