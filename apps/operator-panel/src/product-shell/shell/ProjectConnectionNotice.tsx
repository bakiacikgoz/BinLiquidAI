import { useState } from 'react';
import { createPortal } from 'react-dom';
import { AlertCircle, RotateCcw, X } from 'lucide-react';

export function ProjectConnectionNotice({ detail, onRetry }: { detail: string; onRetry: () => void }) {
  const [collapsed, setCollapsed] = useState(false);
  return createPortal(<aside className="product-connection-notice" aria-label="Çalışma alanı bildirimi">
    {collapsed ? <button type="button" className="connection-notice-reopen" onClick={() => setCollapsed(false)}><AlertCircle size={16} />Bağlantı uyarısı</button> : <div className="connection-notice-card">
      <AlertCircle size={20} className="connection-notice-icon" />
      <div><div role="alert"><strong>Projeler yüklenemedi</strong><p>Çalışma alanına bağlanılamadı. Bağlantıyı yeniden deneyebilirsiniz.</p></div>
        <button type="button" className="connection-notice-retry" onClick={onRetry}><RotateCcw size={14} />Projeleri yeniden yükle</button>
        <details><summary>Teknik ayrıntılar</summary><p>{detail}</p></details>
      </div>
      <button type="button" className="icon-button" aria-label="Bildirimi küçült" onClick={() => setCollapsed(true)}><X size={16} /></button>
    </div>}
  </aside>, document.body);
}
