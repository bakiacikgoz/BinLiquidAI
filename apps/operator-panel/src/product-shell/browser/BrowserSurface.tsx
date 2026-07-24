import { invoke } from '@tauri-apps/api/core';
import { useState } from 'react';

export function BrowserSurface({ onClose }: { onClose: () => void }) {
  const [address, setAddress] = useState('https://');
  const [status, setStatus] = useState('');
  const [sessionLabel, setSessionLabel] = useState<string | null>(null);
  const open = async () => {
    try {
      setStatus('');
      if (sessionLabel) {
        await invoke('browser_navigate', { request: { label: sessionLabel, url: address } });
        setStatus(`Navigated governed browser: ${sessionLabel}`);
      } else {
        const label = await invoke<string>('browser_open', { request: { mode: 'user', url: address } });
        setSessionLabel(label);
        setStatus(`Opened native browser: ${label}`);
      }
    } catch (cause) { setStatus(cause instanceof Error ? cause.message : 'Browser unavailable.'); }
  };
  const close = () => {
    if (sessionLabel) void invoke('browser_close', { request: { label: sessionLabel } });
    onClose();
  };
  const reload = () => { if (sessionLabel) void invoke('browser_reload', { request: { label: sessionLabel } }).catch((cause) => setStatus(cause instanceof Error ? cause.message : 'Browser reload failed.')); };
  return <section className="ps-browser" aria-label="Native browser"><header><strong>Browser</strong><button type="button" onClick={close}>Close</button></header><form onSubmit={(event) => { event.preventDefault(); void open(); }}><input aria-label="Browser address" value={address} onChange={(event) => setAddress(event.target.value)} inputMode="url" /><button type="submit">{sessionLabel ? 'Navigate HTTPS' : 'Open HTTPS'}</button></form><div><button type="button" disabled title="Native browser history is unavailable in the current Tauri runtime.">Back unavailable</button><button type="button" disabled title="Native browser history is unavailable in the current Tauri runtime.">Forward unavailable</button><button type="button" disabled={!sessionLabel} onClick={reload}>Reload</button></div>{status && <p role="status">{status}</p>}<p>User mode opens only explicitly entered HTTPS URLs. Redirects are revalidated by native policy.</p></section>;
}
