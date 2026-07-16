import { screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { getAssistantFixture } from '../../assistant/assistantFixtures';
import type { ArtifactDescriptor, ArtifactRevision } from '../../artifact-workspace/artifactContracts';
import type { ArtifactWorkspaceState } from '../../artifact-workspace/workspaceController';
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

  it('renders searchable navigation, real tabs, history, and governance status chrome', async () => {
    const descriptor: ArtifactDescriptor = {
      artifactId: 'artifact-document',
      workspaceId: 'workspace-1',
      kind: 'document',
      title: 'Launch plan',
      status: 'active',
      schemaVersion: 1,
      dataClass: 'confidential',
      currentRevisionId: 'revision-2',
      currentRevisionNumber: 2,
      sourceSessionId: null,
      sourceTurnId: null,
      createdByType: 'assistant',
      createdById: 'assistant-1',
      updatedById: 'user-1',
      createdAtUtc: '2026-07-16T08:00:00Z',
      updatedAtUtc: '2026-07-16T09:00:00Z',
      archivedAtUtc: null,
      etag: 'etag-2',
      metadata: { policyStatus: 'governed' },
    };
    const revision: ArtifactRevision = {
      revisionId: 'revision-2',
      artifactId: descriptor.artifactId,
      parentRevisionId: 'revision-1',
      baseRevisionId: 'revision-1',
      revisionNumber: 2,
      mutationType: 'replace_content',
      contentRelpath: 'workspace-1/artifact-document/revision-2.json',
      contentSha256: 'a'.repeat(64),
      contentSizeBytes: 64,
      contentEncoding: 'json',
      changeSummary: 'Updated title',
      authorType: 'user',
      authorId: 'user-1',
      idempotencyKey: 'save-2',
      createdAtUtc: '2026-07-16T09:00:00Z',
    };
    const codeArtifact = { ...descriptor, artifactId: 'artifact-code', kind: 'code' as const, title: 'Policy code' };
    const workspaceState: ArtifactWorkspaceState = {
      activeArtifactId: descriptor.artifactId,
      closeGuard: null,
      tabs: [
        {
          artifact: descriptor,
          revision,
          persistedContent: { kind: 'document', schemaVersion: 1, blocks: [] },
          draftContent: { kind: 'document', schemaVersion: 1, blocks: [{ id: 'block-1' }] },
          dirty: true,
          saveState: 'dirty',
          saveError: null,
          conflict: null,
        },
      ],
    };
    const onOpenArtifact = vi.fn();
    const onRequestClose = vi.fn();
    const onLoadMore = vi.fn();
    const { user } = renderOperatorPanel(
      <AssistantWorkbench
        state={getAssistantFixture('running')}
        artifacts={[]}
        selectedArtifactName=""
        onSelectArtifact={vi.fn()}
        onViewRuns={vi.fn()}
        workspaceState={workspaceState}
        catalog={[descriptor, codeArtifact]}
        catalogNextCursor="cursor-2"
        history={[revision]}
        onOpenArtifact={onOpenArtifact}
        onActivateArtifact={vi.fn()}
        onRequestClose={onRequestClose}
        onLoadCatalog={vi.fn()}
        onLoadMoreCatalog={onLoadMore}
        onLoadHistory={vi.fn()}
      />,
    );

    expect(screen.getByRole('tab', { name: /Launch plan/ })).toHaveAttribute('aria-selected', 'true');
    expect(within(screen.getByLabelText('Artifact status')).getByText('Revision 2')).toBeInTheDocument();
    expect(screen.getByText('confidential')).toBeInTheDocument();
    expect(screen.getByText('governed')).toBeInTheDocument();
    expect(screen.getByText('Updated title')).toBeInTheDocument();

    await user.type(screen.getByRole('searchbox', { name: 'Search artifacts' }), 'Policy');
    await user.click(screen.getByRole('button', { name: /Policy code/ }));
    expect(onOpenArtifact).toHaveBeenCalledWith('artifact-code');

    await user.click(screen.getByRole('button', { name: 'Close Launch plan' }));
    expect(onRequestClose).toHaveBeenCalledWith('artifact-document');
    await user.click(screen.getByRole('button', { name: 'Load more artifacts' }));
    expect(onLoadMore).toHaveBeenCalledTimes(1);
  });
});
