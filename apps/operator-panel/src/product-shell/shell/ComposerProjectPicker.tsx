import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Check, Folder, Plus, Search } from 'lucide-react';
import type { ProductWorkspaceProject } from '../adapters/productWorkspaceClient';

const normalizeSearch = (value: string) => value.toLocaleLowerCase('tr').replaceAll('ı', 'i');

export function ComposerProjectPicker({ projects, projectId, ready, onSelect, onCreate }: {
  projects: ProductWorkspaceProject[]; projectId: string; ready: boolean; onSelect: (id: string) => void; onCreate: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [creating, setCreating] = useState(false);
  const anchor = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const selected = projects.find((project) => project.projectId === projectId);
  const close = () => { setOpen(false); anchor.current?.focus(); };
  useEffect(() => {
    if (!open) return;
    search.current?.focus();
    const outside = (event: PointerEvent) => { if (!panel.current?.contains(event.target as Node) && !anchor.current?.contains(event.target as Node)) setOpen(false); };
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') { setOpen(false); anchor.current?.focus(); } };
    const resize = () => setOpen(false);
    document.addEventListener('pointerdown', outside); document.addEventListener('keydown', escape); window.addEventListener('resize', resize);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape); window.removeEventListener('resize', resize); };
  }, [open]);
  const rect = anchor.current?.getBoundingClientRect();
  return <>
    <button ref={anchor} className="composer-chip composer-project-trigger" type="button" aria-label="Project" aria-haspopup="dialog" aria-expanded={open} disabled={!ready} onClick={() => { setQuery(''); setOpen(!open); }}><Folder size={14} /><span>{selected?.title || 'Proje seç'}</span></button>
    {open && rect && createPortal(<div ref={panel} role="dialog" aria-label="Proje seç" className="composer-project-menu" style={{ left: Math.max(12, Math.min(rect.left, window.innerWidth - 274)), ...(rect.top > window.innerHeight / 2 ? { bottom: window.innerHeight - rect.top + 6, maxHeight: rect.top - 18 } : { top: rect.bottom + 6, maxHeight: window.innerHeight - rect.bottom - 18 }) }}>
      <label className="composer-project-search"><Search size={14} /><input ref={search} aria-label="Proje ara" placeholder="Proje ara" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
      <div className="composer-project-options" role="listbox" aria-label="Projeler">
        {projects.filter((project) => normalizeSearch(project.title).includes(normalizeSearch(query))).map((project) => <button type="button" role="option" aria-selected={projectId === project.projectId} key={project.projectId} onClick={() => { onSelect(project.projectId); close(); }}><Folder size={14} /><span>{project.title}</span>{projectId === project.projectId && <Check size={13} />}</button>)}
        {!projects.some((project) => normalizeSearch(project.title).includes(normalizeSearch(query))) && <p className="composer-project-empty">{projects.length ? 'Proje bulunamadı' : 'Henüz proje yok'}</p>}
      </div>
      <button className="composer-project-create" type="button" disabled={creating} onClick={async () => { setCreating(true); try { await onCreate(); close(); } finally { setCreating(false); } }}><Plus size={14} />{creating ? 'Klasör seçiliyor…' : 'Yeni proje'}</button>
    </div>, document.body)}
  </>;
}
