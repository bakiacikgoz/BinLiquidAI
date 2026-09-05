import { useState } from 'react';
import { Plus, Terminal, X } from 'lucide-react';
import { TerminalSurface } from '../terminal/TerminalSurface';
import { useProductShellStore } from '../state/productShellStore';

export function TerminalDock({ open, projectRootRef, projectRootDisplayName }: { open: boolean; projectRootRef?: string; projectRootDisplayName?: string }) {
  const [tabs, setTabs] = useState([{ id: 'terminal-1', title: 'Terminal 1' }]);
  const [active, setActive] = useState('terminal-1');
  const [next, setNext] = useState(2);
  const height = useProductShellStore((state) => state.dockHeight);
  const setHeight = useProductShellStore((state) => state.setDockHeight);
  const closeDock = () => useProductShellStore.getState().setDockOpen(false);
  const add = () => { const id = `terminal-${next}`; setTabs((current) => [...current, { id, title: `Terminal ${next}` }]); setActive(id); setNext(next + 1); };
  const close = (id: string) => { const remaining = tabs.filter((tab) => tab.id !== id); setTabs(remaining); if (id === active) setActive(remaining.at(-1)?.id || ''); };
  return <section className="bottom-dock terminal-dock" hidden={!open} style={{ height }} aria-label="Terminal paneli">
    <div className="dock-resize" role="separator" tabIndex={0} aria-label="Terminal yüksekliği" aria-orientation="horizontal" aria-valuemin={140} aria-valuemax={520} aria-valuenow={height} onKeyDown={(event) => { if(event.key === 'ArrowUp' || event.key === 'ArrowDown') { event.preventDefault(); setHeight(height + (event.key === 'ArrowUp' ? 20 : -20)); } }} onPointerDown={(event) => { event.currentTarget.setPointerCapture(event.pointerId); }} onPointerMove={(event) => { if(event.currentTarget.hasPointerCapture(event.pointerId)) setHeight(window.innerHeight - event.clientY); }} />
    <header><div role="tablist" aria-label="Terminal sekmeleri" className="terminal-dock-tabs">{tabs.map((tab) => <div key={tab.id}><button type="button" role="tab" aria-selected={tab.id === active} onClick={() => setActive(tab.id)}><Terminal size={13}/><span title={projectRootDisplayName || tab.title}>{projectRootDisplayName || tab.title}</span></button><button type="button" aria-label={`${tab.title} kapat`} onClick={() => close(tab.id)}><X size={12}/></button></div>)}<button type="button" aria-label="Yeni terminal" onClick={add}><Plus size={15}/></button></div><button type="button" className="icon-button" aria-label="Terminal panelini kapat" onClick={closeDock}><X size={15}/></button></header>
    {tabs.map((tab) => <div className="terminal-dock-surface" role="tabpanel" key={tab.id} hidden={tab.id !== active}><TerminalSurface active={open && tab.id === active} projectRootRef={projectRootRef} projectRootDisplayName={projectRootDisplayName} onClose={() => close(tab.id)}/></div>)}
    {!tabs.length && <button type="button" className="quiet-button" onClick={add}>Yeni terminal aç</button>}
  </section>;
}
