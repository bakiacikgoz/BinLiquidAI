import type { AssistantSessionState } from '../../assistant/assistantTypes';
import type { ProductTask } from '../state/productShellStore';

export function ContextRail({ task, state }: { task?: ProductTask; state: AssistantSessionState }) {
  return <aside className="ps-rail" aria-label="Task context"><h3>Context</h3>
    <dl><dt>Task</dt><dd>{task?.title ?? 'No task selected'}</dd><dt>Task state</dt><dd>{task?.status ?? '—'}</dd><dt>Assistant session</dt><dd>{state.sessionId || 'Not started'}</dd><dt>Active turn</dt><dd>{state.activeTurnId ?? 'No active turn'}</dd><dt>Runtime state</dt><dd>{state.status.replace('_', ' ')}</dd><dt>Referenced artifacts</dt><dd>{state.referencedArtifacts.length}</dd></dl>
  </aside>;
}
