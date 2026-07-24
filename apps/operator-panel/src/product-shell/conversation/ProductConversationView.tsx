import { useEffect, useState } from 'react';
import type { AssistantSessionState } from '../../assistant/assistantTypes';
import { productWorkspaceClient } from '../adapters/productWorkspaceClient';
import { transientConversationTurns, type StoredMessage } from './conversationState';

export function ProductConversationView({ state, taskId, refreshToken = 0, onOpenArtifacts, onRegenerate }: { state: AssistantSessionState; taskId: string; refreshToken?: number; onOpenArtifacts?: (artifactId?: string) => void; onRegenerate?: (turnId: string) => void }) {
  const [stored, setStored] = useState<StoredMessage[]>([]);
  useEffect(() => { void productWorkspaceClient.listMessages(taskId).then(({ messages }) => setStored(messages)).catch(() => undefined); }, [refreshToken, taskId]);
  const transient = transientConversationTurns(state, stored);
  if (!state.turns.length && !stored.length) return <section className="ps-empty"><h2>Start governed work</h2><p>ImperaOS will plan, enforce policy, and keep a trace of the run.</p></section>;
  return <section className="ps-conversation" aria-label="Assistant conversation">
    {stored.map((message) => <article className="ps-turn" key={message.messageId}><p className="ps-turn-user">{message.role}: {message.body}</p><button type="button" onClick={() => void globalThis.navigator?.clipboard?.writeText(message.body)}>Copy</button></article>)}
    {transient.map((turn) => <article className="ps-turn" key={turn.id}>
      {turn.user && <p className="ps-turn-user">{turn.user}</p>}
      {turn.status && <p className="ps-turn-status">{turn.status}</p>}
      {turn.assistant && <p>{turn.assistant}</p>}
      {(turn.assistant || turn.user) && <div><button type="button" onClick={() => void globalThis.navigator?.clipboard?.writeText(turn.assistant ?? turn.user ?? '')}>Copy</button>{turn.assistant && onRegenerate && <button type="button" onClick={() => onRegenerate(turn.id)}>Regenerate</button>}</div>}
    </article>)}
    {state.referencedArtifacts.filter((artifact) => artifact.openable && artifact.artifactId).map((artifact) => <article className="ps-artifact-card" key={`${artifact.artifactId}:${artifact.revisionId ?? ''}`}><strong>{artifact.name}</strong><span>{artifact.kind ?? 'artifact'} · {artifact.summary ?? 'Governed artifact available'}</span><button type="button" onClick={() => onOpenArtifacts?.(artifact.artifactId)}>Open in workspace</button></article>)}
  </section>;
}
