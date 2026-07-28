import { FileText, Globe2, MonitorPlay, TerminalSquare } from 'lucide-react';

export function WorkSurface({
  taskTitle,
  onOpenArtifacts,
  onOpenTerminal,
  onOpenBrowser,
  onOpenPreview,
}: {
  taskTitle: string;
  onOpenArtifacts: () => void;
  onOpenTerminal: () => void;
  onOpenBrowser: () => void;
  onOpenPreview: () => void;
}) {
  return (
    <section className="workspace-launcher" aria-label="Artifact workspace">
      <button type="button" className="open-surface-prompt" onClick={onOpenArtifacts}>
        Belge taslağını çalışma yüzeyinde aç
      </button>
      <div className="workspace-launcher-menu" aria-label="Governed workspace surfaces">
        <button type="button" onClick={onOpenArtifacts}><FileText size={15} />Open Artifact Workspace</button>
        <button type="button" onClick={onOpenTerminal}><TerminalSquare size={15} />Open terminal</button>
        <button type="button" onClick={onOpenBrowser}><Globe2 size={15} />Open browser</button>
        <button type="button" onClick={onOpenPreview}><MonitorPlay size={15} />Open preview</button>
        <button type="button" disabled title="Agent browser remains unavailable until a qualified task or deployment policy supplies a domain allowlist." data-disabled-reason="AGENT_BROWSER_CAPABILITY_UNQUALIFIED">Agent browser unavailable</button>
        <button type="button" disabled title="A governed project-files capability is not registered in this desktop runtime." data-disabled-reason="PROJECT_FILES_CAPABILITY_UNAVAILABLE">Files unavailable</button>
        <button type="button" disabled title="A governed data-query capability is not registered in this desktop runtime." data-disabled-reason="DATA_EXPLORER_CAPABILITY_UNAVAILABLE">Data explorer unavailable</button>
      </div>
      <p className="sr-only">{taskTitle} has no selected artifact yet. Create or select one through an approved assistant action.</p>
    </section>
  );
}
