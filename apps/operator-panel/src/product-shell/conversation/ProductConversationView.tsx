import { useEffect, useState } from 'react';
import type { AssistantSessionState } from '../../assistant/assistantTypes';
import { productWorkspaceClient } from '../adapters/productWorkspaceClient';

type StoredMessage = { messageId: string; role: 'user' | 'assistant' | 'system'; body: string; createdAtUtc: string };

export function ProductConversationView({ state, taskId }: { state: AssistantSessionState; taskId: string }) {
  const [stored, setStored] = useState<StoredMessage[]>([]);
  useEffect(() => { void productWorkspaceClient.listMessages(taskId).then(({ messages }) => setStored(messages)).catch(() => undefined); }, [taskId]);
  if (!state.turns.length && !stored.length) return <section className="ps-empty"><h2>Start governed work</h2><p>ImperaOS will plan, enforce policy, and keep a trace of the run.</p></section>;
  return <section className="ps-conversation" aria-label="Assistant conversation">
    {stored.map((message) => <article className="ps-turn" key={message.messageId}><p className="ps-turn-user">{message.role}: {message.body}</p></article>)}
    {state.turns.map((turn) => <article className="ps-turn" key={turn.id}>
      <p className="ps-turn-user">{turn.userMessage.text}</p>
      <p className="ps-turn-status">{turn.status.replace('_', ' ')}</p>
      {turn.assistantMessage.text && <p>{turn.assistantMessage.text}</p>}
    </article>)}
  </section>;
}
