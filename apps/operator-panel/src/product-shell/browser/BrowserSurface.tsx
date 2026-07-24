import { invoke } from '@tauri-apps/api/core';
import { useState } from 'react';

export function BrowserSurface({ onClose }: { onClose: () => void }) {
  const [address, setAddress] = useState('https://');
  const [status, setStatus] = useState('');
  const open = async () => {
    try {
      setStatus('');
      const label = await invoke<string>('browser_open', { request: { mode: 'user', url: address } });
      setStatus(`Opened isolated native browser: ${label}`);
    } catch (cause) { setStatus(cause instanceof Error ? cause.message : 'Browser unavailable.'); }
  };
  return <section className="ps-browser" aria-label="Native browser"><header><strong>Browser</strong><button type="button" onClick={onClose}>Close</button></header><form onSubmit={(event) => { event.preventDefault(); void open(); }}><input aria-label="Browser address" value={address} onChange={(event) => setAddress(event.target.value)} inputMode="url" /><button type="submit">Open HTTPS</button></form>{status && <p role="status">{status}</p>}<p>User mode opens only explicitly entered HTTPS URLs. Redirects are revalidated by native policy.</p></section>;
}
