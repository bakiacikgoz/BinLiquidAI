import { CircleDot, FileText, Folder, ShieldCheck, Terminal, X, ExternalLink } from 'lucide-react';
import type { AssistantSessionState } from '../../assistant/assistantTypes';
import { useProductShellStore, type ProductTask } from '../state/productShellStore';

export function ContextRail({ task, state, onOpenArtifacts, onOpenTerminal }: {
  task?: ProductTask; state: AssistantSessionState;
  onOpenArtifacts?: (id?: string) => void; onOpenTerminal?: () => void;
}) {
  const setContextRailOpen = useProductShellStore((shell) => shell.setContextRailOpen);
  const project = useProductShellStore((shell) => shell.projects.find((item) => item.projectId === task?.projectId));
  const runs = [...new Map(state.turns.flatMap((turn) => turn.assistantMessage.referencedRuns).map((run) => [run.id, run])).values()];
  const artifacts = [...new Map(state.referencedArtifacts.filter((item) => item.artifactId).map((item) => [item.artifactId, item])).values()];
  const attachments = [...new Set(state.turns.flatMap((turn) => turn.composerControls?.contextAttachmentKinds ?? []))];
  const status = { idle: 'Hazır', starting: 'Başlatılıyor', streaming: 'Çalışıyor', completed: 'Tamamlandı', failed: 'Başarısız', cancelled: 'Durduruldu', awaiting_approval: 'Onay bekliyor' }[state.status];
  return <aside className="context-rail reference-environment-rail" aria-label="Task context">
    <header><span>Ortam</span><button type="button" className="icon-button" title="Paneli kapat" onClick={() => setContextRailOpen(false)}><X size={15} /></button></header>
    <div className="environment-rows">
      <div className="environment-row" title={project?.rootDisplayName || task?.title}><Folder size={15} /><span>{project?.rootDisplayName || task?.title || 'Proje'}</span></div>
      <div className="environment-row"><CircleDot size={15} /><span>{status}</span></div>
      {onOpenArtifacts && <button type="button" className="environment-row" onClick={() => onOpenArtifacts()}><FileText size={15} /><span>Çıktıları incele</span><ExternalLink size={13} /></button>}
      {onOpenTerminal && <button type="button" className="environment-row" onClick={onOpenTerminal}><Terminal size={15} /><span>Terminali aç</span><ExternalLink size={13} /></button>}
      {state.pendingApprovalId && <a className="environment-row" href={`#/approvals?approval=${encodeURIComponent(state.pendingApprovalId)}`}><ShieldCheck size={15} /><span>Onayı incele</span></a>}
    </div>
    {runs.length > 0 && <section className="environment-section"><h2>Çalışmalar</h2>{runs.map((run) => <details key={run.id} className="environment-run"><summary><Terminal size={14} /><span>{run.summary || run.id}</span></summary><p>{run.id} · {run.status || 'Durum bildirilmedi'}</p></details>)}</section>}
    <section className="environment-section environment-sources"><h2>Kaynaklar</h2>
      {artifacts.map((item) => <button type="button" className="environment-source" key={item.artifactId} disabled={!item.openable || !onOpenArtifacts} onClick={() => onOpenArtifacts?.(item.artifactId)} title={item.name}><FileText size={14} /><span>{item.name}</span></button>)}
      {attachments.map((item) => <div className="environment-source" key={item}><FileText size={14} /><span>{({ active_run: 'Etkin çalışma', event_tail: 'Son olaylar', approval_summary: 'Onay özeti', artifact_summary: 'Çıktı özeti', system_health: 'Sistem durumu' })[item]}</span></div>)}
      {!artifacts.length && !attachments.length && <p className="ps-muted">Henüz kaynak yok</p>}
    </section>
  </aside>;
}
