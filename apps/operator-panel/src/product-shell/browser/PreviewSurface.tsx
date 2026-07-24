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

export function PreviewSurface({ onClose }: { onClose: () => void }) {
  const [origins, setOrigins] = useState<string[]>([]);
  const [selected, setSelected] = useState('');
  const [sessionLabel, setSessionLabel] = useState<string | null>(null);
  const [history, setHistory] = useState<BrowserHistoryState>(emptyHistory);
  const [status, setStatus] = useState('');
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
    onClose();
  };
  const reload = () => {
    if (!sessionLabel) return;
    void invoke('browser_reload', { request: { label: sessionLabel } })
      .catch((cause) => setStatus(cause instanceof Error ? cause.message : 'Preview reload failed.'));
  };

  return <section className="ps-browser" aria-label="Native preview"><header><strong>Preview</strong><button type="button" onClick={close}>Close</button></header><label>Registered local origin<select aria-label="Registered preview origin" value={selected} onChange={(event) => setSelected(event.target.value)}><option value="">No verified origin</option>{origins.map((origin) => <option key={origin} value={origin}>{origin}</option>)}</select></label><div><button type="button" disabled={!selected} onClick={() => void open()}>{sessionLabel ? 'Navigate preview' : 'Open preview'}</button><button type="button" disabled={!sessionLabel || !history.canBack} onClick={() => void move('back')}>Back</button><button type="button" disabled={!sessionLabel || !history.canForward} onClick={() => void move('forward')}>Forward</button><button type="button" disabled={!sessionLabel} onClick={reload}>Reload</button></div>{status && <p role="status">{status}</p>}<p>Only ImperaOS runtime-registered localhost origins can be opened; arbitrary local ports and redirect targets outside the registry are denied.</p></section>;
}
