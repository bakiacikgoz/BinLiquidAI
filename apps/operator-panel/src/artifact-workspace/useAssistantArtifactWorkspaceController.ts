import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from 'react';

import type { AssistantSessionState } from '../assistant/assistantTypes';
import { ArtifactAutosaveQueue } from './artifactAutosave';
import { ArtifactBridgeError, artifactBridge as defaultBridge, type ArtifactBridge } from './artifactBridge';
import type { ArtifactContent, ArtifactDescriptor, ArtifactRevision } from './artifactContracts';
import { exportDocumentArtifact, type DocumentArtifactExportFormat } from './artifactDocumentExport';
import { ArtifactWorkspaceController } from './workspaceController';

export type LegacyWorkbenchArtifact = {
  name: string;
  summary?: string;
  value?: unknown;
};

export type ArtifactWorkspaceUiError = {
  code: string;
  message: string;
  retryable: boolean;
};

export interface AssistantArtifactWorkspaceControllerOptions {
  assistantState: AssistantSessionState;
  legacyArtifacts: LegacyWorkbenchArtifact[];
  selectedLegacyArtifactName: string;
  onSelectLegacyArtifact: (name: string) => void;
  bridge?: ArtifactBridge;
}

function normalizeWorkspaceError(
  error: unknown,
  fallback: ArtifactWorkspaceUiError = {
    code: 'ARTIFACT_WORKSPACE_OPEN_FAILED',
    message: 'The artifact could not be opened.',
    retryable: true,
  },
): ArtifactWorkspaceUiError {
  if (error instanceof ArtifactBridgeError) {
    return {
      code: error.code,
      message: error.message,
      retryable: error.retryable,
    };
  }
  return fallback;
}

export function useAssistantArtifactWorkspaceController({
  assistantState,
  legacyArtifacts,
  selectedLegacyArtifactName,
  onSelectLegacyArtifact,
  bridge = defaultBridge,
}: AssistantArtifactWorkspaceControllerOptions) {
  const [controller] = useState(() => new ArtifactWorkspaceController(bridge));
  const [autosave] = useState(() => new ArtifactAutosaveQueue(controller, bridge));
  const [open, setOpen] = useState(false);
  const [loadingArtifactId, setLoadingArtifactId] = useState<string | null>(null);
  const [error, setError] = useState<ArtifactWorkspaceUiError | null>(null);
  const [operationNotice, setOperationNotice] = useState<string | null>(null);
  const [catalog, setCatalog] = useState<ArtifactDescriptor[]>([]);
  const [catalogNextCursor, setCatalogNextCursor] = useState<string | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [historyByArtifact, setHistoryByArtifact] = useState<Record<string, ArtifactRevision[]>>({});
  const [historyNextCursor, setHistoryNextCursor] = useState<Record<string, string | null>>({});
  const [historyLoadingArtifactId, setHistoryLoadingArtifactId] = useState<string | null>(null);
  const state = useSyncExternalStore(
    useCallback((listener) => controller.subscribe(listener), [controller]),
    useCallback(() => controller.getState(), [controller]),
    useCallback(() => controller.getState(), [controller]),
  );

  useEffect(() => () => autosave.dispose(), [autosave]);

  const loadCatalog = useCallback(
    async (append = false) => {
      setCatalogLoading(true);
      setError(null);
      setOperationNotice(null);
      try {
        const result = await bridge.list({
          cursor: append ? catalogNextCursor ?? undefined : undefined,
          limit: 50,
        });
        setCatalog((previous) => (append ? [...previous, ...result.items] : result.items));
        setCatalogNextCursor(result.nextCursor);
      } catch (caught) {
        setError(normalizeWorkspaceError(caught));
      } finally {
        setCatalogLoading(false);
      }
    },
    [bridge, catalogNextCursor],
  );

  const loadHistory = useCallback(
    async (artifactId: string, append = false) => {
      setHistoryLoadingArtifactId(artifactId);
      setError(null);
      setOperationNotice(null);
      try {
        const result = await bridge.history({
          artifactId,
          cursor: append ? historyNextCursor[artifactId] ?? undefined : undefined,
          limit: 50,
        });
        setHistoryByArtifact((previous) => {
          const combined = append ? [...(previous[artifactId] ?? []), ...result.items] : result.items;
          const seen = new Set<string>();
          return {
            ...previous,
            [artifactId]: combined.filter((revision) => {
              if (seen.has(revision.revisionId)) return false;
              seen.add(revision.revisionId);
              return true;
            }),
          };
        });
        setHistoryNextCursor((previous) => ({ ...previous, [artifactId]: result.nextCursor }));
      } catch (caught) {
        setError(normalizeWorkspaceError(caught));
      } finally {
        setHistoryLoadingArtifactId(null);
      }
    },
    [bridge, historyNextCursor],
  );

  const openArtifact = useCallback(
    async (artifactId: string) => {
      setOpen(true);
      if (controller.getState().tabs.some((tab) => tab.artifact.artifactId === artifactId)) {
        controller.activate(artifactId);
        await loadHistory(artifactId, false);
        return;
      }
      setLoadingArtifactId(artifactId);
      setError(null);
      setOperationNotice(null);
      try {
        await controller.open(artifactId);
        await loadHistory(artifactId, false);
      } catch (caught) {
        setError(normalizeWorkspaceError(caught));
      } finally {
        setLoadingArtifactId(null);
      }
    },
    [controller, loadHistory],
  );

  const edit = useCallback(
    (artifactId: string, content: ArtifactContent) => autosave.schedule(artifactId, content),
    [autosave],
  );

  const restoreArtifact = useCallback(
    async (artifactId: string, revisionId: string) => {
      setError(null);
      setOperationNotice(null);
      try {
        await autosave.flush(artifactId);
        const current = controller.getState().tabs.find((tab) => tab.artifact.artifactId === artifactId);
        if (!current || current.dirty || current.saveState === 'error' || current.saveState === 'conflict') {
          throw new Error('Artifact must be saved before restoring history.');
        }
        if (current.artifact.status === 'archived') throw new Error('Archived artifacts are read-only.');
        const idempotencyKey = `restore:${artifactId}:${revisionId}:${globalThis.crypto.randomUUID()}`;
        await controller.restore(artifactId, revisionId, idempotencyKey);
        await loadHistory(artifactId, false);
        setOperationNotice('Revision restored.');
      } catch (caught) {
        setError(normalizeWorkspaceError(caught, {
          code: 'ARTIFACT_RESTORE_FAILED',
          message: 'The revision could not be restored.',
          retryable: true,
        }));
      }
    },
    [autosave, controller, loadHistory],
  );

  const exportDocument = useCallback(
    async (artifactId: string, format: DocumentArtifactExportFormat) => {
      setError(null);
      setOperationNotice(null);
      try {
        await autosave.flush(artifactId);
        const tab = controller.getState().tabs.find((candidate) => candidate.artifact.artifactId === artifactId);
        if (!tab) throw new Error('Artifact tab is not open.');
        if (tab.dirty || tab.saveState === 'error' || tab.saveState === 'conflict') {
          throw new Error('Artifact must be saved before export.');
        }
        const outcome = await exportDocumentArtifact({
          artifact: tab.artifact,
          revision: tab.revision,
          content: tab.draftContent,
          format,
          bridge,
        });
        setOperationNotice(outcome.status === 'cancelled' ? 'Export cancelled.' : `Exported ${outcome.basename}.`);
        return outcome;
      } catch (caught) {
        setError(normalizeWorkspaceError(caught, {
          code: 'ARTIFACT_EXPORT_FAILED',
          message: 'The document could not be exported.',
          retryable: true,
        }));
        return null;
      }
    },
    [autosave, bridge, controller],
  );

  const reset = useCallback(() => {
    autosave.dispose();
    controller.getState().tabs.forEach((tab) => controller.discardAndClose(tab.artifact.artifactId));
    setOpen(false);
    setLoadingArtifactId(null);
    setError(null);
    setOperationNotice(null);
    setCatalog([]);
    setCatalogNextCursor(null);
    setHistoryByArtifact({});
    setHistoryNextCursor({});
  }, [autosave, controller]);

  const toggle = useCallback(() => {
    if (!open && catalog.length === 0 && !catalogLoading) void loadCatalog(false);
    setOpen((value) => !value);
  }, [catalog.length, catalogLoading, loadCatalog, open]);

  const actions = useMemo(
    () => ({
      toggle,
      reset,
      selectLegacyArtifact: onSelectLegacyArtifact,
      openArtifact,
      activate: (artifactId: string) => controller.activate(artifactId),
      edit,
      flush: (artifactId?: string) => autosave.flush(artifactId),
      retrySave: (artifactId: string) => autosave.retry(artifactId),
      requestClose: (artifactId: string) => controller.requestClose(artifactId),
      cancelClose: () => controller.cancelClose(),
      discardAndClose: (artifactId: string) => controller.discardAndClose(artifactId),
      restore: restoreArtifact,
      exportDocument,
      archive: (artifactId: string) => controller.archive(artifactId),
      clearError: () => setError(null),
      clearOperationNotice: () => setOperationNotice(null),
      loadCatalog: () => loadCatalog(false),
      loadMoreCatalog: () => loadCatalog(true),
      loadHistory: (artifactId: string) => loadHistory(artifactId, false),
      loadMoreHistory: (artifactId: string) => loadHistory(artifactId, true),
    }),
    [autosave, controller, edit, exportDocument, loadCatalog, loadHistory, onSelectLegacyArtifact, openArtifact, reset, restoreArtifact, toggle],
  );

  const activeTab =
    state.tabs.find((tab) => tab.artifact.artifactId === state.activeArtifactId) ?? null;
  const available =
    assistantState.turns.length > 0 ||
    assistantState.referencedArtifacts.length > 0 ||
    legacyArtifacts.length > 0 ||
    state.tabs.length > 0;

  return {
    open,
    available,
    state,
    activeTab,
    loadingArtifactId,
    error,
    operationNotice,
    legacyArtifacts,
    selectedLegacyArtifactName,
    catalog,
    catalogNextCursor,
    catalogLoading,
    history: activeTab ? historyByArtifact[activeTab.artifact.artifactId] ?? [] : [],
    historyNextCursor: activeTab ? historyNextCursor[activeTab.artifact.artifactId] ?? null : null,
    historyLoadingArtifactId,
    actions,
  };
}
