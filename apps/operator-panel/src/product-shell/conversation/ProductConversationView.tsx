import type { AssistantSessionState } from '../../assistant/assistantTypes';

export function ProductConversationView({ state }: { state: AssistantSessionState }) {
  if (!state.turns.length) return <section className="ps-empty"><h2>Start governed work</h2><p>ImperaOS will plan, enforce policy, and keep a trace of the run.</p></section>;
  return <section className="ps-conversation" aria-label="Assistant conversation">
    {state.turns.map((turn) => <article className="ps-turn" key={turn.id}>
      <p className="ps-turn-user">{turn.userMessage.text}</p>
      <p className="ps-turn-status">{turn.status.replace('_', ' ')}</p>
      {turn.assistantMessage.text && <p>{turn.assistantMessage.text}</p>}
    </article>)}
  </section>;
}
