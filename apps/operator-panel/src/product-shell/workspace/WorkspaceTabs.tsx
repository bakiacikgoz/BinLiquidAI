import type { AssistantSessionState } from '../../assistant/assistantTypes';
import { BrowserSurface } from '../browser/BrowserSurface';
import { PreviewSurface } from '../browser/PreviewSurface';
import { TerminalSurface } from '../terminal/TerminalSurface';
import { ProductArtifactWorkspace } from './ProductArtifactWorkspace';
import type { WorkspaceTab } from './workspaceTabState';

export function WorkspaceTabs({
  tabs,
  activeTabId,
  assistantState,
  onActivate,
  onClose,
}: {
  tabs: WorkspaceTab[];
  activeTabId: string | null;
  assistantState: AssistantSessionState;
  onActivate: (tabId: string) => void;
  onClose: (tabId: string) => void;
}) {
  const active = tabs.find((tab) => tab.id === activeTabId) ?? null;
  if (!active) return <section className="ps-workspace-tabs" aria-label="Workspace tabs"><p className="ps-muted">Open an artifact or runtime surface to create a governed workspace tab.</p></section>;
  return <section className="ps-workspace-tabs" aria-label="Workspace tabs"><div className="ps-tab-strip" role="tablist" aria-label="Workspace surfaces">{tabs.map((tab) => <div key={tab.id}><button type="button" role="tab" aria-selected={tab.id === active.id} onClick={() => onActivate(tab.id)}>{tab.title}</button><button type="button" aria-label={`Close ${tab.title}`} onClick={() => onClose(tab.id)}>×</button></div>)}</div><div className="ps-tab-panel" role="tabpanel">{active.kind === 'artifacts' && <ProductArtifactWorkspace state={assistantState} openRequest={1} />}{active.kind === 'terminal' && <TerminalSurface onClose={() => onClose(active.id)} />}{active.kind === 'browser' && <BrowserSurface onClose={() => onClose(active.id)} />}{active.kind === 'preview' && <PreviewSurface onClose={() => onClose(active.id)} />}</div></section>;
}
