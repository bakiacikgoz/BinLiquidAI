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
  return <section className="ps-workspace" aria-label="Artifact workspace">
    <div><strong>Workspace</strong><span>Governed artifacts open in the existing Artifact Workspace.</span></div>
    <div><button type="button" onClick={onOpenArtifacts}>Open Artifact Workspace</button><button type="button" onClick={onOpenTerminal}>Open terminal</button><button type="button" onClick={onOpenBrowser}>Open browser</button><button type="button" onClick={onOpenPreview}>Open preview</button><button type="button" disabled title="A governed project-files capability is not registered in this desktop runtime." data-disabled-reason="PROJECT_FILES_CAPABILITY_UNAVAILABLE">Files unavailable</button><button type="button" disabled title="A governed data-query capability is not registered in this desktop runtime." data-disabled-reason="DATA_EXPLORER_CAPABILITY_UNAVAILABLE">Data explorer unavailable</button></div>
    <p>{taskTitle} has no selected artifact yet. Create or select one through an approved assistant action.</p>
  </section>;
}
