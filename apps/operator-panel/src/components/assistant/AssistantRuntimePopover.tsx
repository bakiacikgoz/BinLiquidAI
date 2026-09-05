import { useEffect, useLayoutEffect, useRef, useState, useId, type ReactNode, type CSSProperties } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, X } from 'lucide-react';

export function AssistantRuntimePopover({ label, locale, children }: { label: string; locale: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<CSSProperties>({});
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const id = useId();
  const close = () => { setOpen(false); trigger.current?.focus(); };
  useLayoutEffect(() => {
    if (!open) return;
    const place = () => {
      const rect = trigger.current?.getBoundingClientRect();
      if (!rect) return;
      const width = Math.min(304, window.innerWidth - 32);
      const above = rect.top > window.innerHeight - rect.bottom;
      setPosition({ position: 'fixed', width, left: Math.max(16, Math.min(rect.right - width, window.innerWidth - width - 16)),
        ...(above ? { bottom: window.innerHeight - rect.top + 8, top: 'auto', maxHeight: Math.max(100, rect.top - 24) }
          : { top: rect.bottom + 8, bottom: 'auto', maxHeight: Math.max(100, window.innerHeight - rect.bottom - 24) }) });
    };
    place();
    window.addEventListener('resize', place);
    window.addEventListener('scroll', place, true);
    panel.current?.querySelector<HTMLElement>('.quick-effort-model-trigger')?.focus();
    return () => { window.removeEventListener('resize', place); window.removeEventListener('scroll', place, true); };
  }, [open]);
  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {
      if (!panel.current?.contains(event.target as Node) && !trigger.current?.contains(event.target as Node)) setOpen(false);
    };
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') { event.preventDefault(); close(); } };
    document.addEventListener('pointerdown', outside);
    document.addEventListener('keydown', escape);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape); };
  }, [open]);
  return <div className="model-picker">
    <button ref={trigger} type="button" className="composer-model" aria-expanded={open} aria-controls={open ? id : undefined} aria-haspopup="dialog" onClick={() => setOpen(!open)}>
      <span>{label}</span><ChevronDown size={14} />
    </button>
    {open && createPortal(<div ref={panel} id={id} className="product-model-menu" style={position} role="dialog" aria-label={locale === 'tr' ? 'Model ayarları' : 'Model settings'}>
      <header className="product-model-menu-heading"><div><strong>{locale === 'tr' ? 'Çalışma ayarları' : 'Runtime settings'}</strong></div><button type="button" className="icon-button" onClick={close} aria-label={locale === 'tr' ? 'Kapat' : 'Close'}><X size={18} /></button></header>
      {children}
    </div>, document.body)}
  </div>;
}
