import { useState } from 'react';
import { TerminalSurface } from '../terminal/TerminalSurface';

export function WorkSurface({ taskTitle }: { taskTitle: string }) {
  const [terminalOpen, setTerminalOpen] = useState(false);
  return <section className="ps-workspace" aria-label="Artifact workspace">
    <div><strong>Workspace</strong><span>Governed artifacts open in the existing Artifact Workspace.</span></div>
    <div><button type="button" onClick={() => window.dispatchEvent(new CustomEvent('imperaos:open-artifact-workspace'))}>Open Artifact Workspace</button><button type="button" onClick={() => setTerminalOpen(true)}>Open terminal</button></div>
    <p>{taskTitle} has no selected artifact yet. Create or select one through an approved assistant action.</p>
    {terminalOpen && <TerminalSurface onClose={() => setTerminalOpen(false)} />}
  </section>;
}
