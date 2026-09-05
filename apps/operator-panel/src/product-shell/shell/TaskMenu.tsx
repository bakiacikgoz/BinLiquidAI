import { useEffect, useRef, useState } from 'react';
import { Archive, Copy, MoreHorizontal, Pencil, Pin, SquarePen } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { productWorkspaceClient } from '../adapters/productWorkspaceClient';
import { useProductShellStore, type ProductTask } from '../state/productShellStore';

export function TaskMenu({ task }: { task: ProductTask }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [rename, setRename] = useState(false);
  const [title, setTitle] = useState(task.title);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => { if (!host.current?.contains(event.target as Node)) setOpen(false); };
    const escape = (event: KeyboardEvent) => { if(event.key === 'Escape') {setOpen(false); host.current?.querySelector('button')?.focus();} };
    document.addEventListener('pointerdown', outside); document.addEventListener('keydown', escape);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape); };
  }, [open]);
  const action = async (work: () => Promise<void>) => { setBusy(true); setError(''); try { await work(); setOpen(false); } catch(cause) { setError(cause instanceof Error ? cause.message : 'İşlem tamamlanamadı.'); } finally { setBusy(false); } };
  const update = async (changes: {title?: string; pinned?: boolean}) => { const result = await productWorkspaceClient.updateTask(task.id, changes); useProductShellStore.getState().upsertTasks([{...task,title:result.title,pinned:result.pinned}]); };
  return <div className="task-title-menu" ref={host}><button className="icon-button" type="button" aria-label="Sohbet seçenekleri" aria-expanded={open} onClick={() => {setOpen(!open); setRename(false); setError('');}}><MoreHorizontal size={16}/></button>
    {open && <div className="task-title-popup" role="menu" aria-label="Sohbet seçenekleri">
      {rename ? <form onSubmit={(event) => {event.preventDefault(); void action(() => update({title:title.trim()}));}}><label>Sohbet adı<input aria-label="Sohbet adı" value={title} maxLength={240} onChange={(event) => setTitle(event.target.value)}/></label><button type="submit" disabled={busy || !title.trim()}>Kaydet</button></form> : <>
      <button role="menuitem" disabled={busy} onClick={() => {setTitle(task.title); setRename(true);}}><Pencil size={14}/>Yeniden adlandır</button>
      <button role="menuitem" disabled={busy} onClick={() => void action(() => update({pinned:!task.pinned}))}><Pin size={14}/>{task.pinned ? 'Sabitlemeyi kaldır' : 'Sabitle'}</button>
      <button role="menuitem" disabled={busy} onClick={() => void action(async () => {await productWorkspaceClient.archiveTask(task.id,'Kullanıcı sohbet menüsünden arşivledi'); useProductShellStore.getState().upsertTasks([{...task,status:'archived'}]); navigate('/');})}><Archive size={14}/>Arşivle</button>
      <hr/>
      <button role="menuitem" disabled={busy} onClick={() => void action(async () => {const {messages} = await productWorkspaceClient.listMessages(task.id); await navigator.clipboard.writeText(messages.map((message) => `${message.role}: ${message.body}`).join('\n\n'));})}><Copy size={14}/>Sohbeti kopyala</button>
      <button role="menuitem" disabled={busy} onClick={() => void action(async () => {await navigator.clipboard.writeText(task.title);})}><Copy size={14}/>Başlığı kopyala</button>
      <hr/>
      <button role="menuitem" onClick={() => {setOpen(false); navigate(task.projectId ? `/?project=${encodeURIComponent(task.projectId)}` : '/');}}><SquarePen size={14}/>Bu projede yeni sohbet</button>
      </>}
      {error && <p role="alert">{error}</p>}
    </div>}
  </div>;
}
