import type { AssistantSessionState } from '../../assistant/assistantTypes';

export function BottomDock({ state }: { state: AssistantSessionState }) {
  const completedTurns = state.turns.filter((turn) => turn.status === 'completed').length;
  const timelineItems = state.turns.reduce((count, turn) => count + turn.assistantMessage.timeline.length, 0);
  const runRefs = new Set(state.turns.flatMap((turn) => turn.assistantMessage.referencedRuns.map((run) => run.id)));
  return <section className="ps-dock" aria-label="Activity"><strong>Activity</strong><span>{state.status === 'idle' ? 'No active run' : `Assistant ${state.status.replace('_', ' ')}`}</span><span>{state.turns.length} recorded turn{state.turns.length === 1 ? '' : 's'} · {completedTurns} complete</span><span>{state.referencedArtifacts.length} artifact reference{state.referencedArtifacts.length === 1 ? '' : 's'}</span><span>{runRefs.size} governed run reference{runRefs.size === 1 ? '' : 's'}</span><span>{timelineItems} runtime timeline item{timelineItems === 1 ? '' : 's'}</span><span>{state.pendingApprovalId ? `Approval pending: ${state.pendingApprovalId}` : 'No pending approval'}</span><span>{state.activeTurnId ? `Active turn: ${state.activeTurnId}` : 'No active turn'}</span></section>;
}
