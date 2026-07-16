import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from 'react';

import type { AssistantSessionState } from '../assistant/assistantTypes';
import { ArtifactAutosaveQueue } from './artifactAutosave';
import { ArtifactBridgeError, artifactBridge as defaultBridge, type ArtifactBridge } from './artifactBridge';
import type { ArtifactContent, ArtifactDescriptor, ArtifactRevision } from './artifactContracts';
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

function normalizeWorkspaceError(error: unknown): ArtifactWorkspaceUiError {
  if (error instanceof ArtifactBridgeError) {
    return {
      code: error.code,
      message: error.message,
      retryable: error.retryable,
    };
  }
  return {
    code: 'ARTIFACT_WORKSPACE_OPEN_FAILED',
    message: 'The artifact could not be opened.',
    retryable: true,
  };
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
      try {
        const result = await bridge.history({
          artifactId,
          cursor: append ? historyNextCursor[artifactId] ?? undefined : undefined,
          limit: 50,
        });
        setHistoryByArtifact((previous) => ({
          ...previous,
          [artifactId]: append ? [...(previous[artifactId] ?? []), ...result.items] : result.items,
        }));
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
      setLoadingArtifactId(artifactId);
      setError(null);
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

  const reset = useCallback(() => {
    autosave.dispose();
    controller.getState().tabs.forEach((tab) => controller.discardAndClose(tab.artifact.artifactId));
    setOpen(false);
    setLoadingArtifactId(null);
    setError(null);
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
      restore: (artifactId: string, revisionId: string, idempotencyKey: string) =>
        controller.restore(artifactId, revisionId, idempotencyKey),
      archive: (artifactId: string) => controller.archive(artifactId),
      clearError: () => setError(null),
      loadCatalog: () => loadCatalog(false),
      loadMoreCatalog: () => loadCatalog(true),
      loadHistory: (artifactId: string) => loadHistory(artifactId, false),
      loadMoreHistory: (artifactId: string) => loadHistory(artifactId, true),
    }),
    [autosave, controller, edit, loadCatalog, loadHistory, onSelectLegacyArtifact, openArtifact, reset, toggle],
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
