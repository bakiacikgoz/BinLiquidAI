import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { Folder, MessageCircle, Pin } from 'lucide-react';

export function SidebarInfoRow({ children, className = '', title, projectTitle, path, count, pinned = false }: {
  children: ReactNode; className?: string; title: string; projectTitle?: string; path?: string; count: number; pinned?: boolean;
}) {
  const row = useRef<HTMLDivElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const [position, setPosition] = useState<{ left: number; top: number; width: number } | null>(null);
  const id = useId();
  const cancelTimer = () => { clearTimeout(timer.current); };
  const hide = () => { cancelTimer(); setPosition(null); };
  const show = () => {
    cancelTimer();
    timer.current = setTimeout(() => {
      const rect = row.current?.getBoundingClientRect();
      if (!rect) return;
      const width = Math.min(320, window.innerWidth - 24);
      setPosition({ width, left: Math.max(12, Math.min(rect.right + 8, window.innerWidth - width - 12)), top: Math.max(12, Math.min(rect.top, window.innerHeight - 220)) });
    }, 550);
  };
  const leave = () => { cancelTimer(); timer.current = setTimeout(() => setPosition(null), 160); };
  useEffect(() => () => clearTimeout(timer.current), []);
  useEffect(() => {
    if (!position) return;
    const close = () => { clearTimeout(timer.current); setPosition(null); };
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') close(); };
    window.addEventListener('scroll', close, true);
    window.addEventListener('resize', close);
    document.addEventListener('keydown', escape);
    return () => { window.removeEventListener('scroll', close, true); window.removeEventListener('resize', close); document.removeEventListener('keydown', escape); };
  }, [position]);
  return <div ref={row} className={`sidebar-row-shell ${className}`} aria-describedby={position ? id : undefined}
    onMouseEnter={show} onMouseLeave={leave} onFocus={show} onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) hide(); }} onClick={hide}>
    {children}
    {position && createPortal(<div id={id} role="tooltip" className="sidebar-info-card" style={{ ...position, maxHeight: window.innerHeight - position.top - 12 }} onMouseEnter={cancelTimer} onMouseLeave={leave}>
      <header><Folder size={16} /><strong>{projectTitle || title}</strong>{pinned && <Pin size={14} />}</header>
      {projectTitle && <p className="sidebar-info-task">{title}</p>}
      <p><MessageCircle size={15} /><span>{count} sohbet</span></p>
      <div className="sidebar-info-path"><Folder size={15} /><span>{path || 'Klasör bilgisi kayıtlı değil'}</span></div>
    </div>, document.body)}
  </div>;
}
