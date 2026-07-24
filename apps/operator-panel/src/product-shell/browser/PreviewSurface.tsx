import { invoke } from '@tauri-apps/api/core';
import { useEffect, useState } from 'react';

export function PreviewSurface({ onClose }: { onClose: () => void }) {
  const [origins, setOrigins] = useState<string[]>([]);
  const [selected, setSelected] = useState('');
  const [status, setStatus] = useState('');
  const [sessionLabel, setSessionLabel] = useState<string | null>(null);
  useEffect(() => {
    void invoke<string[]>('browser_list_preview_origins').then((items) => {
      setOrigins(items);
      setSelected((current) => current || items[0] || '');
    }).catch((cause) => setStatus(cause instanceof Error ? cause.message : 'Preview registry is unavailable.'));
  }, []);
  const open = async () => {
    if (!selected) return;
    try {
      if (sessionLabel) {
        await invoke('browser_navigate', { request: { label: sessionLabel, url: selected } });
        setStatus(`Navigated governed preview: ${sessionLabel}`);
      } else {
        const label = await invoke<string>('browser_open', { request: { mode: 'preview', url: selected } });
        setSessionLabel(label);
        setStatus(`Opened governed preview: ${label}`);
      }
    } catch (cause) { setStatus(cause instanceof Error ? cause.message : 'Preview unavailable.'); }
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
  return <section className="ps-browser" aria-label="Native preview"><header><strong>Preview</strong><button type="button" onClick={close}>Close</button></header><label>Registered local origin<select aria-label="Registered preview origin" value={selected} onChange={(event) => setSelected(event.target.value)}><option value="">No verified origin</option>{origins.map((origin) => <option key={origin} value={origin}>{origin}</option>)}</select></label><div><button type="button" disabled={!selected} onClick={() => void open()}>{sessionLabel ? 'Navigate preview' : 'Open preview'}</button><button type="button" disabled={!sessionLabel} onClick={reload}>Reload</button></div>{status && <p role="status">{status}</p>}<p>Only ImperaOS runtime-registered localhost origins can be opened; arbitrary local ports are denied.</p></section>;
}
