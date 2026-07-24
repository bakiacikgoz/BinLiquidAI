import { useEffect, useState } from 'react';
import type { AssistantSessionState } from '../../assistant/assistantTypes';
import { productWorkspaceClient, type ProductTaskLink } from '../adapters/productWorkspaceClient';
import { transientConversationTurns, type StoredMessage } from './conversationState';

export function ProductConversationView({ state, taskId, refreshToken = 0, onOpenArtifacts, onOpenApproval, onRegenerate }: { state: AssistantSessionState; taskId: string; refreshToken?: number; onOpenArtifacts?: (artifactId?: string) => void; onOpenApproval?: (approvalId: string) => void; onRegenerate?: (turnId: string) => void }) {
  const [stored, setStored] = useState<StoredMessage[]>([]);
  const [links, setLinks] = useState<ProductTaskLink[]>([]);
  useEffect(() => {
    void Promise.all([productWorkspaceClient.listMessages(taskId), productWorkspaceClient.listLinks(taskId)])
      .then(([{ messages }, { links: nextLinks }]) => { setStored(messages); setLinks(nextLinks); })
      .catch(() => undefined);
  }, [refreshToken, taskId]);
  const transient = transientConversationTurns(state, stored);
  if (!state.turns.length && !stored.length) return <section className="ps-empty"><h2>Start governed work</h2><p>ImperaOS will plan, enforce policy, and keep a trace of the run.</p></section>;
  return <section className="ps-conversation" aria-label="Assistant conversation">
    {stored.map((message) => <article className="ps-turn" key={message.messageId}><p className="ps-turn-user">{message.role}: {message.body}</p><button type="button" onClick={() => void globalThis.navigator?.clipboard?.writeText(message.body)}>Copy</button></article>)}
    {transient.map((turn) => {
      const approval = state.turns.find((candidate) => candidate.id === turn.id)?.assistantMessage.approval;
      return <article className="ps-turn" key={turn.id}>
      {turn.user && <p className="ps-turn-user">{turn.user}</p>}
      {turn.status && <p className="ps-turn-status">{turn.status}</p>}
      {turn.assistant && <p>{turn.assistant}</p>}
      {(turn.assistant || turn.user) && <div><button type="button" onClick={() => void globalThis.navigator?.clipboard?.writeText(turn.assistant ?? turn.user ?? '')}>Copy</button>{turn.assistant && onRegenerate && <button type="button" onClick={() => onRegenerate(turn.id)}>Regenerate</button>}{approval && onOpenApproval && <button type="button" onClick={() => onOpenApproval(approval.approvalId)}>Open approval</button>}{turn.assistant && <button type="button" disabled title="No governed feedback sink is registered for assistant turns." data-disabled-reason="ASSISTANT_FEEDBACK_CAPABILITY_UNAVAILABLE">Feedback unavailable</button>}</div>}
    </article>;
    })}
    {state.referencedArtifacts.filter((artifact) => artifact.openable && artifact.artifactId).map((artifact) => <article className="ps-artifact-card" key={`${artifact.artifactId}:${artifact.revisionId ?? ''}`}><strong>{artifact.name}</strong><span>{artifact.kind ?? 'artifact'} · {artifact.summary ?? 'Governed artifact available'}</span><button type="button" onClick={() => onOpenArtifacts?.(artifact.artifactId)}>Open in workspace</button></article>)}
    {links.length ? <section className="ps-durable-links" aria-label="Durable task links"><h3>Durable task links</h3>{links.map((link) => <div key={link.linkId}><code>{link.targetType}</code><span>{link.targetId}</span>{link.targetType === 'artifact' && <button type="button" onClick={() => onOpenArtifacts?.(link.targetId)}>Open artifact {link.targetId}</button>}{link.targetType === 'approval' && <button type="button" onClick={() => onOpenApproval?.(link.targetId)}>Open approval {link.targetId}</button>}{link.targetType === 'run' && <span className="ps-muted">Governed run reference</span>}{link.targetType === 'team_job' && <span className="ps-muted">Governed team job reference</span>}</div>)}</section> : null}
  </section>;
}
