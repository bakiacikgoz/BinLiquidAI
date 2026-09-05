import { useEffect, useRef, useState, type ReactNode, type RefObject } from 'react';
import { createPortal } from 'react-dom';
import { Check, ChevronRight, Plus } from 'lucide-react';

export function SidebarTaskMenu({ anchor, onClose, grouping, onGrouping, sort, onSort, onCreateSection, children }: {
  anchor: RefObject<HTMLButtonElement | null>; onClose: () => void; grouping: string; onGrouping: (value: string) => void;
  sort: string; onSort: (value: string) => void; onCreateSection: (name: string) => void; children: ReactNode;
}) {
  const menu = useRef<HTMLDivElement>(null);
  const [sub, setSub] = useState('');
  const [name, setName] = useState('');
  const rect = anchor.current?.getBoundingClientRect();
  useEffect(() => {
    const outside = (event: PointerEvent) => { if (!menu.current?.contains(event.target as Node) && !anchor.current?.contains(event.target as Node)) onClose(); };
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') { onClose(); anchor.current?.focus(); } };
    document.addEventListener('pointerdown', outside); document.addEventListener('keydown', escape);
    const scroll = (event: Event) => { if (!menu.current?.contains(event.target as Node)) onClose(); };
    window.addEventListener('resize', onClose); window.addEventListener('scroll', scroll, true);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape); window.removeEventListener('resize', onClose); window.removeEventListener('scroll', scroll, true); };
  }, [anchor, onClose]);
  if (!rect) return null;
  return createPortal(<div ref={menu} className="sidebar-task-menu" role="dialog" aria-label="Sohbet düzeni" style={{ left: Math.max(8, Math.min(rect.left, window.innerWidth - (window.innerWidth > 650 ? 430 : 256))), ...(rect.top > window.innerHeight / 2 ? { bottom: window.innerHeight - rect.top + 6 } : { top: rect.bottom + 6 }) }}>
    {[
      { id: 'group', label: 'Kenar çubuğunu düzenle', values: [['project', 'Projeye göre'], ['flat', 'Tek listede']], current: grouping, change: onGrouping },
      { id: 'sort', label: 'Sohbetleri sıralama ölçütü', values: [['priority', 'Öncelik'], ['recent', 'Son güncelleme'], ['manual', 'Manuel sıralama']], current: sort, change: onSort },
    ].map((item) => <div key={item.id} className="sidebar-submenu-row" onMouseEnter={() => setSub(item.id)}>
      <button type="button" aria-expanded={sub === item.id} onClick={() => setSub(item.id)} onKeyDown={(event) => { if (event.key === 'ArrowRight') setSub(item.id); }}>{item.label}<ChevronRight size={14} /></button>
      {sub === item.id && <div className="sidebar-task-submenu" role="group" aria-label={item.label}>
        {item.values.map(([value, label]) => <button type="button" role="menuitemradio" aria-checked={item.current === value} key={value} onClick={() => { item.change(value); onClose(); }}><span className="menu-radio">{item.current === value && <Check size={12} />}</span>{label}</button>)}
      </div>}
    </div>)}
    <button type="button" className="sidebar-menu-new-section" onClick={() => setSub('new')}><Plus size={15} />Yeni bölüm</button>
    {sub === 'new' && <form onSubmit={(event) => { event.preventDefault(); if (name.trim()) { onCreateSection(name.trim()); onClose(); } }}><input aria-label="Bölüm adı" placeholder="Bölüm adı" maxLength={60} value={name} onChange={(event) => setName(event.target.value)} /><button type="submit" disabled={!name.trim()}>Oluştur</button></form>}
    <details className="sidebar-menu-filters"><summary>Filtrele ve yenile</summary>{children}</details>
  </div>, document.body);
}
