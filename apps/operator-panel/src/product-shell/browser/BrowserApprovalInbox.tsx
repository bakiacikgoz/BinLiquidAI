import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { useEffect, useState } from 'react';

type BrowserMode = 'user' | 'preview' | 'agent';
type BrowserApprovalRequest = {
  kind: 'new_window' | 'download' | 'external_application';
  url: string;
  mode: BrowserMode;
  taskId?: string | null;
};

export function BrowserApprovalInbox() {
  const [request, setRequest] = useState<BrowserApprovalRequest | null>(null);
  const [status, setStatus] = useState('');

  useEffect(() => {
    let unlisten: (() => void) | undefined;
    void listen<BrowserApprovalRequest>('browser://approval-required', (event) => {
      setStatus('');
      setRequest(event.payload);
    }).then((dispose) => { unlisten = dispose; });
    return () => unlisten?.();
  }, []);

  if (!request) return status ? <p className="ps-browser-status" role="status">{status}</p> : null;

  const openApprovedWindow = async () => {
    try {
      await invoke<string>('browser_open', {
        request: {
          mode: request.mode,
          url: request.url,
          taskId: request.taskId ?? undefined,
        },
      });
      setStatus('Approved browser window opened under the same mode policy.');
    } catch (cause) {
      setStatus(cause instanceof Error ? cause.message : 'Browser approval could not be completed.');
    } finally {
      setRequest(null);
    }
  };

  const isPopup = request.kind === 'new_window';
  const title = isPopup
    ? 'A new browser window needs your approval.'
    : request.kind === 'download'
      ? 'A download needs your approval.'
      : 'An external application needs your approval.';

  return <section className="ps-browser-approval" role="alertdialog" aria-label="Browser approval required">
    <strong>{title}</strong>
    <code>{request.url}</code>
    <p>{isPopup
      ? 'The popup was blocked until you explicitly approve opening it in a governed browser window.'
      : request.kind === 'download'
        ? 'Browser downloads stay blocked until ImperaOS has a governed save-and-approval workflow.'
        : 'External applications stay blocked; no operating-system application will be opened from the browser.'}</p>
    <div>
      {isPopup ? <button type="button" onClick={() => void openApprovedWindow()}>Approve and open</button> : null}
      <button type="button" onClick={() => setRequest(null)}>{isPopup ? 'Deny' : 'Acknowledge and keep blocked'}</button>
    </div>
  </section>;
}
