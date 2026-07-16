import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react';

import type { AssistantSessionState } from '../assistant/assistantTypes';
import { ArtifactAutosaveQueue } from './artifactAutosave';
import { ArtifactBridgeError, artifactBridge as defaultBridge, type ArtifactBridge } from './artifactBridge';
import { compareArtifactContent, type ArtifactDiffResult } from './artifactDiff';
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

export type ArtifactRevisionComparison = {
  artifactId: string;
  selectedRevisionId: string;
  afterRevisionId: string;
  status: 'loading' | 'ready' | 'error';
  beforeRevisionNumber: number | null;
  afterRevisionNumber: number;
  dirtyDraftExcluded: boolean;
  result: ArtifactDiffResult | null;
  error: ArtifactWorkspaceUiError | null;
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
  const [comparison, setComparison] = useState<ArtifactRevisionComparison | null>(null);
  const comparisonRequestSequence = useRef(0);
  const state = useSyncExternalStore(
    useCallback((listener) => controller.subscribe(listener), [controller]),
    useCallback(() => controller.getState(), [controller]),
    useCallback(() => controller.getState(), [controller]),
  );

  const invalidateComparison = useCallback(() => {
    comparisonRequestSequence.current += 1;
    setComparison(null);
  }, []);

  useEffect(() => () => autosave.dispose(), [autosave]);

  useEffect(() => {
    if (!comparison) return;
    const tab = state.tabs.find((candidate) => candidate.artifact.artifactId === comparison.artifactId);
    if (!tab || tab.revision.revisionId !== comparison.afterRevisionId) invalidateComparison();
  }, [comparison, invalidateComparison, state.tabs]);

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
      invalidateComparison();
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
    [controller, invalidateComparison, loadHistory],
  );

  const edit = useCallback(
    (artifactId: string, content: ArtifactContent) => autosave.schedule(artifactId, content),
    [autosave],
  );

  const compareRevision = useCallback(
    async (artifactId: string, revisionId: string) => {
      const tab = controller.getState().tabs.find((candidate) => candidate.artifact.artifactId === artifactId);
      if (!tab) return;
      const requestSequence = ++comparisonRequestSequence.current;
      setComparison({
        artifactId,
        selectedRevisionId: revisionId,
        afterRevisionId: tab.revision.revisionId,
        status: 'loading',
        beforeRevisionNumber: null,
        afterRevisionNumber: tab.revision.revisionNumber,
        dirtyDraftExcluded: tab.dirty,
        result: null,
        error: null,
      });
      try {
        const historical = await bridge.get({ artifactId, revisionId });
        if (requestSequence !== comparisonRequestSequence.current) return;
        if (
          historical.artifact.artifactId !== artifactId ||
          historical.revision.artifactId !== artifactId ||
          historical.revision.revisionId !== revisionId
        ) {
          throw new Error('Historical revision identity mismatch.');
        }
        const current = controller.getState().tabs.find((candidate) => candidate.artifact.artifactId === artifactId);
        if (!current || current.artifact.kind !== historical.artifact.kind) {
          throw new Error('Artifact comparison context changed.');
        }
        if (current.revision.revisionId !== tab.revision.revisionId) {
          throw new Error('Artifact comparison context changed.');
        }
        setComparison({
          artifactId,
          selectedRevisionId: revisionId,
          afterRevisionId: current.revision.revisionId,
          status: 'ready',
          beforeRevisionNumber: historical.revision.revisionNumber,
          afterRevisionNumber: current.revision.revisionNumber,
          dirtyDraftExcluded: current.dirty,
          result: compareArtifactContent(historical.content, current.persistedContent),
          error: null,
        });
      } catch (caught) {
        if (requestSequence !== comparisonRequestSequence.current) return;
        setComparison({
          artifactId,
          selectedRevisionId: revisionId,
          afterRevisionId: tab.revision.revisionId,
          status: 'error',
          beforeRevisionNumber: null,
          afterRevisionNumber: tab.revision.revisionNumber,
          dirtyDraftExcluded: tab.dirty,
          result: null,
          error: normalizeWorkspaceError(caught, {
            code: 'ARTIFACT_COMPARISON_FAILED',
            message: 'The selected revisions could not be compared.',
            retryable: true,
          }),
        });
      }
    },
    [bridge, controller],
  );

  const closeComparison = useCallback(() => {
    invalidateComparison();
  }, [invalidateComparison]);

  const restoreArtifact = useCallback(
    async (artifactId: string, revisionId: string) => {
      invalidateComparison();
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
    [autosave, controller, invalidateComparison, loadHistory],
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
    invalidateComparison();
  }, [autosave, controller, invalidateComparison]);

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
      activate: (artifactId: string) => {
        invalidateComparison();
        controller.activate(artifactId);
      },
      edit,
      compareRevision,
      closeComparison,
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
    [autosave, closeComparison, compareRevision, controller, edit, exportDocument, invalidateComparison, loadCatalog, loadHistory, onSelectLegacyArtifact, openArtifact, reset, restoreArtifact, toggle],
  );

  const activeTab =
    state.tabs.find((tab) => tab.artifact.artifactId === state.activeArtifactId) ?? null;
  const available =
    assistantState.turns.length > 0 ||
    assistantState.referencedArtifacts.length > 0 ||
    legacyArtifacts.length > 0 ||
    state.tabs.length > 0;
  const visibleComparison = comparison
    && activeTab?.artifact.artifactId === comparison.artifactId
    && activeTab.revision.revisionId === comparison.afterRevisionId
    ? comparison
    : null;

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
    comparison: visibleComparison,
    actions,
  };
}
