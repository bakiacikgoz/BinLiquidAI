import type { AssistantSessionState } from '../../assistant/assistantTypes';

export function BottomDock({ state }: { state: AssistantSessionState }) {
  return <section className="ps-dock" aria-label="Activity"><strong>Activity</strong><span>{state.status === 'idle' ? 'No active run' : `Assistant ${state.status.replace('_', ' ')}`}</span><span>{state.turns.length} recorded turn{state.turns.length === 1 ? '' : 's'}</span></section>;
}
