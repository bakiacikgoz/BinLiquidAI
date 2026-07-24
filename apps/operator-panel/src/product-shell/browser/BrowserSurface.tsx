import { invoke } from '@tauri-apps/api/core';
import { useEffect, useState } from 'react';

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

export function BrowserSurface({ onClose }: { onClose: () => void }) {
  const [address, setAddress] = useState('https://');
  const [sessionLabel, setSessionLabel] = useState<string | null>(null);
  const [history, setHistory] = useState<BrowserHistoryState>(emptyHistory);
  const [status, setStatus] = useState('');

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

  return <section className="ps-browser" aria-label="Native browser"><header><strong>Browser</strong><button type="button" onClick={close}>Close</button></header><form onSubmit={(event) => { event.preventDefault(); void open(); }}><input aria-label="Browser address" value={address} onChange={(event) => setAddress(event.target.value)} inputMode="url" /><button type="submit">{sessionLabel ? 'Navigate HTTPS' : 'Open HTTPS'}</button></form><div><button type="button" disabled={!sessionLabel || !history.canBack} onClick={() => void move('back')}>Back</button><button type="button" disabled={!sessionLabel || !history.canForward} onClick={() => void move('forward')}>Forward</button><button type="button" disabled={!sessionLabel} onClick={reload}>Reload</button></div>{status && <p role="status">{status}</p>}<p>User mode opens only explicitly entered HTTPS URLs. Each explicit history target and every redirect is revalidated by native policy.</p></section>;
}
