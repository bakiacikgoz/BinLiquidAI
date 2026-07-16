import { artifactBridge as defaultBridge, type ArtifactBridge } from './artifactBridge';
import type {
  ArtifactContent,
  ArtifactDescriptor,
  ArtifactOperationResult,
  ArtifactReadResult,
  ArtifactRevision,
} from './artifactContracts';


export type ArtifactSaveState = 'idle' | 'dirty' | 'saving' | 'saved' | 'error' | 'conflict';

export interface ArtifactConflict {
  remoteRevisionNumber: number;
  remoteRevisionId: string;
  detectedAtUtc: string;
}

export interface ArtifactWorkspaceTab {
  artifact: ArtifactDescriptor;
  revision: ArtifactRevision;
  persistedContent: ArtifactContent;
  draftContent: ArtifactContent;
  dirty: boolean;
  saveState: ArtifactSaveState;
  saveError: string | null;
  conflict: ArtifactConflict | null;
}

export interface ArtifactWorkspaceState {
  tabs: ArtifactWorkspaceTab[];
  activeArtifactId: string | null;
  closeGuard: { artifactId: string; reason: 'dirty' | 'saving' } | null;
}

export type ArtifactWorkspaceAction =
  | { type: 'opened'; result: ArtifactReadResult }
  | { type: 'activated'; artifactId: string }
  | { type: 'edited'; artifactId: string; content: ArtifactContent }
  | { type: 'saveStarted'; artifactId: string }
  | {
      type: 'saveSucceeded';
      artifactId: string;
      operation: ArtifactOperationResult;
      content: ArtifactContent;
    }
  | { type: 'saveFailed'; artifactId: string; message: string }
  | { type: 'saveConflicted'; artifactId: string; remote: ArtifactReadResult }
  | { type: 'metadataUpdated'; operation: ArtifactOperationResult }
  | { type: 'closeRequested'; artifactId: string }
  | { type: 'closeCancelled' }
  | { type: 'closeDiscarded'; artifactId: string };

export function createArtifactWorkspaceState(): ArtifactWorkspaceState {
  return { tabs: [], activeArtifactId: null, closeGuard: null };
}

function tabFromRead(result: ArtifactReadResult): ArtifactWorkspaceTab {
  return {
    artifact: result.artifact,
    revision: result.revision,
    persistedContent: result.content,
    draftContent: result.content,
    dirty: false,
    saveState: 'idle',
    saveError: null,
    conflict: null,
  };
}

function replaceTab(
  state: ArtifactWorkspaceState,
  artifactId: string,
  update: (tab: ArtifactWorkspaceTab) => ArtifactWorkspaceTab,
): ArtifactWorkspaceState {
  if (!state.tabs.some((tab) => tab.artifact.artifactId === artifactId)) {
    return state;
  }
  return {
    ...state,
    tabs: state.tabs.map((tab) => (tab.artifact.artifactId === artifactId ? update(tab) : tab)),
  };
}

function closeTab(state: ArtifactWorkspaceState, artifactId: string): ArtifactWorkspaceState {
  const index = state.tabs.findIndex((tab) => tab.artifact.artifactId === artifactId);
  if (index < 0) {
    return { ...state, closeGuard: null };
  }
  const tabs = state.tabs.filter((tab) => tab.artifact.artifactId !== artifactId);
  const activeArtifactId =
    state.activeArtifactId === artifactId
      ? (tabs[Math.min(index, tabs.length - 1)]?.artifact.artifactId ?? null)
      : state.activeArtifactId;
  return { tabs, activeArtifactId, closeGuard: null };
}

export function artifactWorkspaceReducer(
  state: ArtifactWorkspaceState,
  action: ArtifactWorkspaceAction,
): ArtifactWorkspaceState {
  switch (action.type) {
    case 'opened': {
      const artifactId = action.result.artifact.artifactId;
      const tab = tabFromRead(action.result);
      const exists = state.tabs.some((item) => item.artifact.artifactId === artifactId);
      return {
        ...state,
        tabs: exists
          ? state.tabs.map((item) => (item.artifact.artifactId === artifactId ? tab : item))
          : [...state.tabs, tab],
        activeArtifactId: artifactId,
        closeGuard: null,
      };
    }
    case 'activated':
      return state.tabs.some((tab) => tab.artifact.artifactId === action.artifactId)
        ? { ...state, activeArtifactId: action.artifactId }
        : state;
    case 'edited':
      return replaceTab(state, action.artifactId, (tab) => ({
        ...tab,
        draftContent: action.content,
        dirty: true,
        saveState: 'dirty',
        saveError: null,
        conflict: null,
      }));
    case 'saveStarted':
      return replaceTab(state, action.artifactId, (tab) => ({
        ...tab,
        saveState: 'saving',
        saveError: null,
      }));
    case 'saveSucceeded':
      return replaceTab(state, action.artifactId, (tab) => ({
        ...tab,
        artifact: action.operation.artifact,
        revision: action.operation.revision,
        persistedContent: action.content,
        draftContent: action.content,
        dirty: false,
        saveState: action.operation.disposition === 'no_op' ? 'idle' : 'saved',
        saveError: null,
        conflict: null,
      }));
    case 'saveFailed':
      return replaceTab(state, action.artifactId, (tab) => ({
        ...tab,
        dirty: true,
        saveState: 'error',
        saveError: action.message,
      }));
    case 'saveConflicted':
      return replaceTab(state, action.artifactId, (tab) => ({
        ...tab,
        dirty: true,
        saveState: 'conflict',
        saveError: null,
        conflict: {
          remoteRevisionNumber: action.remote.revision.revisionNumber,
          remoteRevisionId: action.remote.revision.revisionId,
          detectedAtUtc: new Date().toISOString(),
        },
      }));
    case 'metadataUpdated':
      return replaceTab(state, action.operation.artifact.artifactId, (tab) => ({
        ...tab,
        artifact: action.operation.artifact,
        revision: action.operation.revision,
        dirty: false,
        saveState: 'idle',
        saveError: null,
        conflict: null,
      }));
    case 'closeRequested': {
      const tab = state.tabs.find((item) => item.artifact.artifactId === action.artifactId);
      if (!tab) return state;
      if (tab.saveState === 'saving' || tab.dirty) {
        return {
          ...state,
          closeGuard: {
            artifactId: action.artifactId,
            reason: tab.saveState === 'saving' ? 'saving' : 'dirty',
          },
        };
      }
      return closeTab(state, action.artifactId);
    }
    case 'closeCancelled':
      return { ...state, closeGuard: null };
    case 'closeDiscarded':
      return closeTab(state, action.artifactId);
  }
}

type WorkspaceListener = (state: ArtifactWorkspaceState) => void;

export class ArtifactWorkspaceController {
  private state = createArtifactWorkspaceState();
  private readonly listeners = new Set<WorkspaceListener>();
  private readonly bridge: ArtifactBridge;

  constructor(bridge: ArtifactBridge = defaultBridge) {
    this.bridge = bridge;
  }

  getState(): ArtifactWorkspaceState {
    return this.state;
  }

  subscribe(listener: WorkspaceListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  dispatch(action: ArtifactWorkspaceAction): void {
    const next = artifactWorkspaceReducer(this.state, action);
    if (next === this.state) return;
    this.state = next;
    this.listeners.forEach((listener) => listener(this.state));
  }

  async open(artifactId: string): Promise<void> {
    const result = await this.bridge.get({ artifactId });
    this.dispatch({ type: 'opened', result });
  }

  activate(artifactId: string): void {
    this.dispatch({ type: 'activated', artifactId });
  }

  edit(artifactId: string, content: ArtifactContent): void {
    this.dispatch({ type: 'edited', artifactId, content });
  }

  requestClose(artifactId: string): void {
    this.dispatch({ type: 'closeRequested', artifactId });
  }

  cancelClose(): void {
    this.dispatch({ type: 'closeCancelled' });
  }

  discardAndClose(artifactId: string): void {
    this.dispatch({ type: 'closeDiscarded', artifactId });
  }

  async restore(artifactId: string, sourceRevisionId: string, idempotencyKey: string): Promise<void> {
    const tab = this.requireTab(artifactId);
    await this.bridge.restore({
      artifactId,
      sourceRevisionId,
      expectedRevisionNumber: tab.artifact.currentRevisionNumber,
      idempotencyKey,
      changeSummary: 'Revision restored',
    });
    await this.open(artifactId);
  }

  async archive(artifactId: string): Promise<void> {
    const tab = this.requireTab(artifactId);
    const operation = await this.bridge.archive({
      artifactId,
      expectedRevisionNumber: tab.artifact.currentRevisionNumber,
    });
    this.dispatch({ type: 'metadataUpdated', operation });
  }

  private requireTab(artifactId: string): ArtifactWorkspaceTab {
    const tab = this.state.tabs.find((item) => item.artifact.artifactId === artifactId);
    if (!tab) throw new Error('Artifact tab is not open.');
    return tab;
  }
}
