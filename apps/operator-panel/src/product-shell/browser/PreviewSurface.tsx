import { invoke } from '@tauri-apps/api/core';
import { useEffect, useState } from 'react';

export function PreviewSurface({ onClose }: { onClose: () => void }) {
  const [origins, setOrigins] = useState<string[]>([]);
  const [selected, setSelected] = useState('');
  const [status, setStatus] = useState('');
  useEffect(() => {
    void invoke<string[]>('browser_list_preview_origins').then((items) => {
      setOrigins(items);
      setSelected((current) => current || items[0] || '');
    }).catch((cause) => setStatus(cause instanceof Error ? cause.message : 'Preview registry is unavailable.'));
  }, []);
  const open = async () => {
    if (!selected) return;
    try {
      const label = await invoke<string>('browser_open', { request: { mode: 'preview', url: selected } });
      setStatus(`Opened governed preview: ${label}`);
    } catch (cause) { setStatus(cause instanceof Error ? cause.message : 'Preview unavailable.'); }
  };
  return <section className="ps-browser" aria-label="Native preview"><header><strong>Preview</strong><button type="button" onClick={onClose}>Close</button></header><label>Registered local origin<select aria-label="Registered preview origin" value={selected} onChange={(event) => setSelected(event.target.value)}><option value="">No verified origin</option>{origins.map((origin) => <option key={origin} value={origin}>{origin}</option>)}</select></label><button type="button" disabled={!selected} onClick={() => void open()}>Open preview</button>{status && <p role="status">{status}</p>}<p>Only ImperaOS runtime-registered localhost origins can be opened; arbitrary local ports are denied.</p></section>;
}
