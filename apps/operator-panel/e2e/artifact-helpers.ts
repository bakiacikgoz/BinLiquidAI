import type { Page } from '@playwright/test';

export async function installArtifactBridgeStub(page: Page): Promise<void> {
  await page.evaluate(() => {
    const now = '2026-07-16T09:00:00Z';
    const contents = new Map<string, unknown>();
    let descriptor = {
      artifactId: 'artifact-preview-document',
      workspaceId: 'workspace-preview',
      kind: 'document',
      title: 'Launch plan',
      status: 'active',
      schemaVersion: 1,
      dataClass: 'internal',
      currentRevisionId: 'revision-1',
      currentRevisionNumber: 1,
      sourceSessionId: 'assistant-preview-session',
      sourceTurnId: 'assistant-preview-turn',
      createdByType: 'assistant',
      createdById: 'assistant-preview',
      updatedById: 'assistant-preview',
      createdAtUtc: now,
      updatedAtUtc: now,
      archivedAtUtc: null,
      etag: 'etag-1',
      metadata: { policyStatus: 'governed' },
    };
    let revision = {
      revisionId: 'revision-1',
      artifactId: descriptor.artifactId,
      parentRevisionId: null,
      baseRevisionId: null,
      revisionNumber: 1,
      mutationType: 'create',
      contentRelpath: 'workspace-preview/artifact-preview-document/revision-1.json',
      contentSha256: 'a'.repeat(64),
      contentSizeBytes: 64,
      contentEncoding: 'json',
      changeSummary: 'Created by assistant',
      authorType: 'assistant',
      authorId: 'assistant-preview',
      idempotencyKey: 'create-preview-document',
      createdAtUtc: now,
    };
    let content = {
      kind: 'document',
      schemaVersion: 1,
      language: 'en',
      pageMode: 'document',
      blocks: [
        {
          id: 'block-1',
          type: 'paragraph',
          props: {},
          content: [{ type: 'text', text: 'Initial governed draft', styles: {} }],
          children: [],
        },
      ],
    };
    const history = [revision];
    contents.set(revision.revisionId, content);
    const exportRequests: Array<{ command: string; request: Record<string, unknown> }> = [];
    let pendingExportFormat = 'markdown';

    const ok = (data: unknown) => ({ ok: true, data, error: null });
    const operation = () => ({ artifact: descriptor, revision, created: false, disposition: 'updated' });
    const nextRevision = (nextContent: typeof content, mutationType: string, changeSummary: string) => {
      const previous = revision;
      const revisionNumber = previous.revisionNumber + 1;
      descriptor = {
        ...descriptor,
        currentRevisionId: `revision-${revisionNumber}`,
        currentRevisionNumber: revisionNumber,
        updatedById: 'e2e-operator',
        etag: `etag-${revisionNumber}`,
      };
      revision = {
        ...previous,
        revisionId: `revision-${revisionNumber}`,
        parentRevisionId: previous.revisionId,
        revisionNumber,
        mutationType,
        changeSummary,
        authorType: 'user',
        authorId: 'e2e-operator',
        idempotencyKey: `${mutationType}-${revisionNumber}`,
      };
      content = nextContent;
      contents.set(revision.revisionId, content);
      history.unshift(revision);
    };

    (window as unknown as { __artifactE2eState: unknown }).__artifactE2eState = {
      exportRequests,
      snapshot: () => ({ descriptor, revision, content, history: [...history] }),
    };
    (window as unknown as { __TAURI_INTERNALS__: unknown }).__TAURI_INTERNALS__ = {
      invoke: async (command: string, args: Record<string, unknown>) => {
        if (command === 'bridge_artifact_list') return ok({ items: [descriptor], next_cursor: null });
        if (command === 'bridge_artifact_get') return ok({ artifact: descriptor, revision, content });
        if (command === 'bridge_artifact_history') return ok({ items: history, next_cursor: null });
        if (command === 'bridge_artifact_mutate') {
          const params = (args.payload as { params: Record<string, unknown> }).params;
          nextRevision(params.content as typeof content, 'replace_content', String(params.changeSummary ?? 'Autosave'));
          return ok(operation());
        }
        if (command === 'bridge_artifact_restore') {
          const params = (args.payload as { params: Record<string, unknown> }).params;
          const restored = contents.get(String(params.sourceRevisionId));
          if (!restored) throw new Error('Unknown source revision');
          nextRevision(restored as typeof content, 'restore', 'Revision restored');
          return ok(operation());
        }
        if (command === 'bridge_artifact_export_begin') {
          const request = args.request as Record<string, unknown>;
          pendingExportFormat = String(request.format);
          exportRequests.push({ command, request });
          return ok({ cancelled: false, ticket: `ticket-${exportRequests.length}`, expiresInMs: 60_000, maxBytes: 1_000_000 });
        }
        if (command === 'bridge_artifact_export_commit') {
          const request = args.request as { bytes: number[]; sha256: string } & Record<string, unknown>;
          exportRequests.push({ command, request });
          return ok({
            basename: pendingExportFormat === 'html' ? 'launch-plan.html' : 'launch-plan.md',
            sha256: request.sha256,
            sizeBytes: request.bytes.length,
          });
        }
        if (command === 'bridge_artifact_export_cancel') return ok({ cancelled: true });
        throw new Error(`Unexpected artifact E2E command: ${command}`);
      },
    };
  });
}

export async function artifactExportCommands(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const state = (window as unknown as {
      __artifactE2eState: { exportRequests: Array<{ command: string }> };
    }).__artifactE2eState;
    return state.exportRequests.map((item) => item.command);
  });
}
