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
    <div><button type="button" onClick={onOpenArtifacts}>Open Artifact Workspace</button><button type="button" onClick={onOpenTerminal}>Open terminal</button><button type="button" onClick={onOpenBrowser}>Open browser</button><button type="button" onClick={onOpenPreview}>Open preview</button></div>
    <p>{taskTitle} has no selected artifact yet. Create or select one through an approved assistant action.</p>
  </section>;
}
