import { useEffect, useState } from 'react';
import type { AssistantSessionState } from '../../assistant/assistantTypes';
import { productWorkspaceClient } from '../adapters/productWorkspaceClient';
import { transientConversationTurns, type StoredMessage } from './conversationState';

export function ProductConversationView({ state, taskId, refreshToken = 0 }: { state: AssistantSessionState; taskId: string; refreshToken?: number }) {
  const [stored, setStored] = useState<StoredMessage[]>([]);
  useEffect(() => { void productWorkspaceClient.listMessages(taskId).then(({ messages }) => setStored(messages)).catch(() => undefined); }, [refreshToken, taskId]);
  const transient = transientConversationTurns(state, stored);
  if (!state.turns.length && !stored.length) return <section className="ps-empty"><h2>Start governed work</h2><p>ImperaOS will plan, enforce policy, and keep a trace of the run.</p></section>;
  return <section className="ps-conversation" aria-label="Assistant conversation">
    {stored.map((message) => <article className="ps-turn" key={message.messageId}><p className="ps-turn-user">{message.role}: {message.body}</p></article>)}
    {transient.map((turn) => <article className="ps-turn" key={turn.id}>
      {turn.user && <p className="ps-turn-user">{turn.user}</p>}
      {turn.status && <p className="ps-turn-status">{turn.status}</p>}
      {turn.assistant && <p>{turn.assistant}</p>}
    </article>)}
  </section>;
}
