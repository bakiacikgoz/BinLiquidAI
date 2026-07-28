import { invoke } from '@tauri-apps/api/core';
import { ChevronLeft, ChevronRight, RotateCw, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

type BrowserHistoryState = { canBack: boolean; canForward: boolean };

const emptyHistory: BrowserHistoryState = { canBack: false, canForward: false };

function normalizeHistory(value: unknown): BrowserHistoryState {
  if (typeof value !== 'object' || value === null) return emptyHistory;
  const record = value as Record<string, unknown>;
  return {
    canBack: record.canBack === true,
    canForward: record.canForward === true,
  };
}

export function PreviewSurface({ active = true, onClose, sessionLabel: persistedSessionLabel, onSessionChange }: { active?: boolean; onClose: () => void; sessionLabel?: string; onSessionChange?: (sessionLabel: string | null) => void }) {
  const [origins, setOrigins] = useState<string[]>([]);
  const [selected, setSelected] = useState('');
  const [ownedSessionLabel, setOwnedSessionLabel] = useState<string | null>(null);
  const [history, setHistory] = useState<BrowserHistoryState>(emptyHistory);
  const [status, setStatus] = useState('');
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const sessionLabel = persistedSessionLabel ?? ownedSessionLabel;
  const setSessionLabel = (next: string | null) => {
    setOwnedSessionLabel(next);
    onSessionChange?.(next);
  };
  const refreshHistory = async (label = sessionLabel) => {
    if (!label) { setHistory(emptyHistory); return; }
    setHistory(normalizeHistory(await invoke<unknown>('browser_history_state', { request: { label } })));
  };

  useEffect(() => {
    void invoke<string[]>('browser_list_preview_origins').then((items) => {
      setOrigins(items);
      setSelected((current) => current && items.includes(current) ? current : items[0] ?? '');
    }).catch((cause) => setStatus(cause instanceof Error ? cause.message : 'Verified preview origins are unavailable.'));
  }, []);
  useEffect(() => {
    if (!sessionLabel) return;
    void refreshHistory(sessionLabel).catch((cause) => setStatus(cause instanceof Error ? cause.message : 'Preview history is unavailable.'));
  }, [sessionLabel]);
  useEffect(() => {
    if (!sessionLabel || !active || !viewportRef.current) return;
    let mounted = true;
    const synchronize = () => {
      const viewport = viewportRef.current;
      if (!mounted || !viewport) return;
      const bounds = viewport.getBoundingClientRect();
      if (bounds.width <= 0 || bounds.height <= 0) return;
      const request = {
        label: sessionLabel,
        x: Math.round(bounds.x), y: Math.round(bounds.y),
        width: Math.round(bounds.width), height: Math.round(bounds.height),
      };
      void invoke('browser_set_bounds', { request })
        .then(() => invoke('browser_show', { request: { label: sessionLabel } }))
        .catch((cause) => { if (mounted) setStatus(cause instanceof Error ? cause.message : 'Preview viewport could not be synchronized.'); });
    };
    synchronize();
    const observer = typeof ResizeObserver === 'undefined' ? undefined : new ResizeObserver(synchronize);
    observer?.observe(viewportRef.current);
    window.addEventListener('resize', synchronize);
    return () => {
      mounted = false;
      observer?.disconnect();
      window.removeEventListener('resize', synchronize);
      void invoke('browser_hide', { request: { label: sessionLabel } });
    };
  }, [active, sessionLabel]);

  const open = async () => {
    if (!selected) return;
    try {
      if (sessionLabel) {
        await invoke('browser_navigate', { request: { label: sessionLabel, url: selected } });
        await refreshHistory(sessionLabel);
      } else {
        const label = await invoke<string>('browser_open', { request: { mode: 'preview', url: selected } });
        setSessionLabel(label);
        setHistory(emptyHistory);
      }
      setStatus('Opened only the runtime-registered preview origin.');
    } catch (cause) { setStatus(cause instanceof Error ? cause.message : 'Preview navigation failed.'); }
  };
  const move = async (direction: 'back' | 'forward') => {
    if (!sessionLabel) return;
    try {
      await invoke(direction === 'back' ? 'browser_back' : 'browser_forward', { request: { label: sessionLabel } });
      await refreshHistory(sessionLabel);
      setStatus(`Navigated ${direction} through governed preview history.`);
    } catch (cause) { setStatus(cause instanceof Error ? cause.message : 'Preview history navigation failed.'); }
  };
  const close = () => {
    if (sessionLabel) void invoke('browser_close', { request: { label: sessionLabel } });
    setSessionLabel(null);
    onClose();
  };
  const reload = () => {
    if (!sessionLabel) return;
    void invoke('browser_reload', { request: { label: sessionLabel } })
      .catch((cause) => setStatus(cause instanceof Error ? cause.message : 'Preview reload failed.'));
  };

  return (
    <section className="preview-surface" aria-label="Native preview">
      <div className="preview-browser">
        <button type="button" aria-label="Back" disabled={!sessionLabel || !history.canBack} onClick={() => void move('back')}><ChevronLeft size={16} /></button>
        <button type="button" aria-label="Forward" disabled={!sessionLabel || !history.canForward} onClick={() => void move('forward')}><ChevronRight size={16} /></button>
        <button type="button" aria-label="Reload" disabled={!sessionLabel} onClick={reload}><RotateCw size={15} /></button>
        <label className="preview-origin-picker">
          <span className="sr-only">Registered local origin</span>
          <select aria-label="Registered preview origin" value={selected} onChange={(event) => setSelected(event.target.value)}>
            <option value="">No verified origin</option>
            {origins.map((origin) => <option key={origin} value={origin}>{origin}</option>)}
          </select>
        </label>
        <button type="button" disabled={!selected} onClick={() => void open()}>{sessionLabel ? 'Navigate preview' : 'Open preview'}</button>
        <button type="button" aria-label="Close" onClick={close}><X size={16} /></button>
      </div>
      <div ref={viewportRef} className="preview-hero native-preview-viewport" aria-label="Preview page viewport" />
      {status ? <p className="native-surface-status" role="status">{status}</p> : null}
      <p className="native-policy-note">Only ImperaOS runtime-registered localhost origins can be opened; arbitrary local ports and redirect targets outside the registry are denied.</p>
    </section>
  );
}
