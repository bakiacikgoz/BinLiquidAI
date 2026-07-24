import { useState } from 'react';
import { TerminalSurface } from '../terminal/TerminalSurface';
import { BrowserSurface } from '../browser/BrowserSurface';

export function WorkSurface({ taskTitle, onOpenArtifacts }: { taskTitle: string; onOpenArtifacts: () => void }) {
  const [terminalOpen, setTerminalOpen] = useState(false);
  const [browserOpen, setBrowserOpen] = useState(false);
  return <section className="ps-workspace" aria-label="Artifact workspace">
    <div><strong>Workspace</strong><span>Governed artifacts open in the existing Artifact Workspace.</span></div>
    <div><button type="button" onClick={onOpenArtifacts}>Open Artifact Workspace</button><button type="button" onClick={() => setTerminalOpen(true)}>Open terminal</button><button type="button" onClick={() => setBrowserOpen(true)}>Open browser</button></div>
    <p>{taskTitle} has no selected artifact yet. Create or select one through an approved assistant action.</p>
    {terminalOpen && <TerminalSurface onClose={() => setTerminalOpen(false)} />}
    {browserOpen && <BrowserSurface onClose={() => setBrowserOpen(false)} />}
  </section>;
}
