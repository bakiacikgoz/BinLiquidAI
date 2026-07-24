export function WorkSurface({ taskTitle }: { taskTitle: string }) {
  return <section className="ps-workspace" aria-label="Artifact workspace">
    <div><strong>Workspace</strong><span>Governed artifacts open in the existing Artifact Workspace.</span></div>
    <button type="button" onClick={() => window.dispatchEvent(new CustomEvent('imperaos:open-artifact-workspace'))}>Open Artifact Workspace</button>
    <p>{taskTitle} has no selected artifact yet. Create or select one through an approved assistant action.</p>
  </section>;
}
