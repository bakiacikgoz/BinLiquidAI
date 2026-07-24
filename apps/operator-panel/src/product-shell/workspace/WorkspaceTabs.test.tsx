import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../terminal/TerminalSurface', () => ({ TerminalSurface: ({ projectRootRef, active }: { projectRootRef?: string; active?: boolean }) => <div>Terminal surface {projectRootRef ?? 'runtime-root'} · {active ? 'active' : 'inactive'}</div> }));
vi.mock('../browser/BrowserSurface', () => ({ BrowserSurface: () => <div>Browser surface</div> }));
vi.mock('../browser/PreviewSurface', () => ({ PreviewSurface: () => <div>Preview surface</div> }));
vi.mock('./ProductArtifactWorkspace', () => ({ ProductArtifactWorkspace: ({ requestedArtifactId }: { requestedArtifactId?: string }) => <div>Artifact surface {requestedArtifactId ?? 'catalog'}</div> }));

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

    const { user } = renderOperatorPanel(<WorkspaceTabs tabs={[first, second]} activeTabId={second.id} assistantState={getAssistantFixture('running')} onActivate={onActivate} onClose={onClose} onUpdate={vi.fn()} />);

    expect(screen.getByText('Terminal surface runtime-root · active')).toBeInTheDocument();
    await user.click(screen.getAllByRole('tab', { name: 'Terminal' })[0]);
    await user.click(screen.getAllByRole('button', { name: 'Close Terminal' })[1]);

    expect(onActivate).toHaveBeenCalledWith(first.id);
    expect(onClose).toHaveBeenCalledWith(second.id);
  });

  it('hands an artifact-card selection to the canonical artifact workspace', () => {
    const artifact = createWorkspaceTab('artifacts', 'artifact-release-plan');

    renderOperatorPanel(<WorkspaceTabs tabs={[artifact]} activeTabId={artifact.id} assistantState={getAssistantFixture('running')} onActivate={vi.fn()} onClose={vi.fn()} onUpdate={vi.fn()} />);

    expect(screen.getByText('Artifact surface artifact-release-plan')).toBeInTheDocument();
  });

  it('passes only the opaque project-root reference to a user terminal', () => {
    const terminal = createWorkspaceTab('terminal');

    renderOperatorPanel(<WorkspaceTabs tabs={[terminal]} activeTabId={terminal.id} assistantState={getAssistantFixture('running')} projectRootRef="root-release" projectRootDisplayName="Release workspace" onActivate={vi.fn()} onClose={vi.fn()} onUpdate={vi.fn()} />);

    expect(screen.getByText('Terminal surface root-release · active')).toBeInTheDocument();
  });

  it('keeps inactive runtime surfaces mounted so a terminal session survives tab changes', () => {
    const first = createWorkspaceTab('terminal');
    const second = createWorkspaceTab('terminal');

    renderOperatorPanel(<WorkspaceTabs tabs={[first, second]} activeTabId={second.id} assistantState={getAssistantFixture('running')} onActivate={vi.fn()} onClose={vi.fn()} onUpdate={vi.fn()} />);

    expect(screen.getByText('Terminal surface runtime-root · inactive')).toBeInTheDocument();
    expect(screen.getByText('Terminal surface runtime-root · active')).toBeInTheDocument();
  });
});
