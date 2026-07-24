import { invoke } from '@tauri-apps/api/core';
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

export function BrowserSurface({ active = true, onClose, sessionLabel: persistedSessionLabel, onSessionChange }: { active?: boolean; onClose: () => void; sessionLabel?: string; onSessionChange?: (sessionLabel: string | null) => void }) {
  const [address, setAddress] = useState('https://');
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
    const next = await invoke<unknown>('browser_history_state', { request: { label } });
    setHistory(normalizeHistory(next));
  };
  const open = async () => {
    try {
      if (sessionLabel) {
        await invoke('browser_navigate', { request: { label: sessionLabel, url: address } });
        await refreshHistory(sessionLabel);
        setStatus(`Navigated governed browser: ${sessionLabel}`);
      } else {
        const label = await invoke<string>('browser_open', { request: { mode: 'user', url: address } });
        setSessionLabel(label);
        setHistory(emptyHistory);
        setStatus(`Opened native browser: ${label}`);
      }
    } catch (cause) { setStatus(cause instanceof Error ? cause.message : 'Browser navigation failed.'); }
  };
  const move = async (direction: 'back' | 'forward') => {
    if (!sessionLabel) return;
    try {
      await invoke(direction === 'back' ? 'browser_back' : 'browser_forward', { request: { label: sessionLabel } });
      await refreshHistory(sessionLabel);
      setStatus(`Navigated ${direction} through governed browser history.`);
    } catch (cause) { setStatus(cause instanceof Error ? cause.message : 'Browser history navigation failed.'); }
  };
  const close = () => {
    if (sessionLabel) void invoke('browser_close', { request: { label: sessionLabel } });
    setSessionLabel(null);
    onClose();
  };
  const reload = () => {
    if (!sessionLabel) return;
    void invoke('browser_reload', { request: { label: sessionLabel } })
      .catch((cause) => setStatus(cause instanceof Error ? cause.message : 'Browser reload failed.'));
  };

  useEffect(() => {
    if (!sessionLabel) return;
    void refreshHistory(sessionLabel).catch((cause) => setStatus(cause instanceof Error ? cause.message : 'Browser history is unavailable.'));
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
        .catch((cause) => { if (mounted) setStatus(cause instanceof Error ? cause.message : 'Browser viewport could not be synchronized.'); });
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

  return <section className="ps-browser" aria-label="Native browser"><header><strong>Browser</strong><button type="button" onClick={close}>Close</button></header><form onSubmit={(event) => { event.preventDefault(); void open(); }}><input aria-label="Browser address" value={address} onChange={(event) => setAddress(event.target.value)} inputMode="url" /><button type="submit">{sessionLabel ? 'Navigate HTTPS' : 'Open HTTPS'}</button></form><div><button type="button" disabled={!sessionLabel || !history.canBack} onClick={() => void move('back')}>Back</button><button type="button" disabled={!sessionLabel || !history.canForward} onClick={() => void move('forward')}>Forward</button><button type="button" disabled={!sessionLabel} onClick={reload}>Reload</button></div><div ref={viewportRef} className="ps-browser-viewport" aria-label="Browser page viewport" />{status && <p role="status">{status}</p>}<p>User mode opens only explicitly entered HTTPS URLs. Each explicit history target and every redirect is revalidated by native policy.</p></section>;
}
