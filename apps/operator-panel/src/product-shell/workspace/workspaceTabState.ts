export type WorkspaceTabKind = 'artifacts' | 'terminal' | 'browser' | 'preview';
export type WorkspaceTab = { id: string; kind: WorkspaceTabKind; title: string };

const labels: Record<WorkspaceTabKind, string> = {
  artifacts: 'Artifacts',
  terminal: 'Terminal',
  browser: 'Browser',
  preview: 'Preview',
};

export function createWorkspaceTab(kind: WorkspaceTabKind): WorkspaceTab {
  const id = kind === 'artifacts'
    ? 'artifacts'
    : `${kind}-${globalThis.crypto?.randomUUID?.() ?? Date.now().toString(36)}`;
  return { id, kind, title: labels[kind] };
}
