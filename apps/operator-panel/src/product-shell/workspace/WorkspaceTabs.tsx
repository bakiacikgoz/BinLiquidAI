import { FileText, Globe2, MonitorPlay, TerminalSquare, X } from 'lucide-react';

import type { AssistantSessionState } from '../../assistant/assistantTypes';
import { BrowserSurface } from '../browser/BrowserSurface';
import { PreviewSurface } from '../browser/PreviewSurface';
import { TerminalSurface } from '../terminal/TerminalSurface';
import { ProductArtifactWorkspace } from './ProductArtifactWorkspace';
import type { WorkspaceTab } from './workspaceTabState';

const tabIcons = {
  artifacts: FileText,
  terminal: TerminalSquare,
  browser: Globe2,
  preview: MonitorPlay,
} as const;

export function WorkspaceTabs({
  tabs,
  activeTabId,
  assistantState,
  projectRootRef,
  projectRootDisplayName,
  onActivate,
  onClose,
  onUpdate,
}: {
  tabs: WorkspaceTab[];
  activeTabId: string | null;
  assistantState: AssistantSessionState;
  projectRootRef?: string;
  projectRootDisplayName?: string;
  onActivate: (tabId: string) => void;
  onClose: (tabId: string) => void;
  onUpdate: (tabId: string, changes: Partial<WorkspaceTab>) => void;
}) {
  const active = tabs.find((tab) => tab.id === activeTabId) ?? null;
  if (!active) {
    return (
      <section className="workspace-tabs-empty ps-workspace-tabs" aria-label="Workspace tabs">
        <p className="ps-muted">Open an artifact or runtime surface to create a governed workspace tab.</p>
      </section>
    );
  }

  return (
    <section className="workspace-tabs" aria-label="Workspace tabs">
      <header className="workspace-tab-strip">
        <div className="workspace-tab-list">
          <div className="workspace-tab-scroll" role="tablist" aria-label="Workspace surfaces">
            {tabs.map((tab) => {
              const TabIcon = tabIcons[tab.kind];
              const isActive = tab.id === active.id;
              return (
                <div className="workspace-tab-item" key={tab.id}>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={isActive}
                    className={`workspace-tab${isActive ? ' is-active' : ''}`}
                    onClick={() => onActivate(tab.id)}
                  >
                    <TabIcon size={14} />
                    <span>{tab.title}</span>
                  </button>
                  <button
                    type="button"
                    className="workspace-tab-close"
                    aria-label={`Close ${tab.title}`}
                    onClick={() => onClose(tab.id)}
                  >
                    <X size={13} />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </header>
      <div className="surface-content" role="tabpanel">
        {tabs.map((tab) => {
          const isActive = tab.id === active.id;
          return (
            <div className="workspace-runtime-surface" key={tab.id} hidden={!isActive} aria-hidden={!isActive}>
              {tab.kind === 'artifacts' ? <ProductArtifactWorkspace state={assistantState} openRequest={1} requestedArtifactId={tab.artifactId} /> : null}
              {tab.kind === 'terminal' ? <TerminalSurface active={isActive} onClose={() => onClose(tab.id)} projectRootRef={projectRootRef} projectRootDisplayName={projectRootDisplayName} /> : null}
              {tab.kind === 'browser' ? <BrowserSurface active={isActive} onClose={() => onClose(tab.id)} sessionLabel={tab.nativeSessionLabel} onSessionChange={(nativeSessionLabel) => onUpdate(tab.id, { nativeSessionLabel: nativeSessionLabel ?? undefined })} /> : null}
              {tab.kind === 'preview' ? <PreviewSurface active={isActive} onClose={() => onClose(tab.id)} sessionLabel={tab.nativeSessionLabel} onSessionChange={(nativeSessionLabel) => onUpdate(tab.id, { nativeSessionLabel: nativeSessionLabel ?? undefined })} /> : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}
