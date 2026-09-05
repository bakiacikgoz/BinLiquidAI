import { useEffect, useState } from 'react';
import { ChevronRight, CircleCheck, Terminal, AlertCircle } from 'lucide-react';
import type { AssistantTurn } from '../../assistant/assistantTypes';

export function TurnActivity({ turn }: { turn: AssistantTurn }) {
  const running = turn.status === 'starting' || turn.status === 'streaming';
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [running]);
  const end = turn.completedAtUtc ? Date.parse(turn.completedAtUtc) : now;
  const seconds = Math.max(0, Math.floor((end - Date.parse(turn.startedAtUtc)) / 1000));
  const duration = Number.isFinite(seconds) ? `${seconds >= 60 ? `${Math.floor(seconds / 60)} dk ` : ''}${seconds % 60} sn` : '';
  const label = running ? 'süredir çalışıyor' : ({ starting: 'başlatılıyor', streaming: 'çalışıyor', completed: 'çalıştı', failed: 'çalışma başarısız', cancelled: 'durduruldu', awaiting_approval: 'onay bekliyor', idle: 'hazır' }[turn.status] ?? '');
  const items = turn.assistantMessage.timeline;
  return <div className={`turn-activity ${running ? 'is-running' : ''}`}>
    <details open={running || undefined}>
      <summary><span className="turn-status-dot" aria-hidden="true" /><span>{duration} {label}</span><ChevronRight size={13} /></summary>
      {items.length > 0 && <ol aria-label="Çalışma adımları">{items.map((item) => <li key={item.id} className={`activity-tone-${item.tone}`}>
        <details><summary>{item.tone === 'success' ? <CircleCheck size={14} /> : item.tone === 'error' || item.tone === 'warning' ? <AlertCircle size={14} /> : <Terminal size={14} />}<span>{item.title}</span><span className="activity-subtitle">{item.subtitle}</span></summary><p>{item.subtitle}</p><time dateTime={item.timestampUtc}>{new Date(item.timestampUtc).toLocaleTimeString('tr-TR')}</time></details>
      </li>)}</ol>}
      {!items.length && running && <p className="activity-awaiting">Model yanıtı bekleniyor<span className="activity-ellipsis" aria-hidden="true">…</span></p>}
    </details>
    {turn.assistantMessage.error && <p className="turn-error" role="alert">{turn.assistantMessage.error.message}</p>}
    {turn.assistantMessage.warning && <p className="turn-warning">{turn.assistantMessage.warning}</p>}
  </div>;
}
