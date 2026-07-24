import type { AssistantSessionState } from '../../assistant/assistantTypes';
import type { ProductTask } from '../state/productShellStore';

function unique(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}

export function ContextRail({ task, state }: { task?: ProductTask; state: AssistantSessionState }) {
  const runs = unique(state.turns.flatMap((turn) => turn.assistantMessage.referencedRuns.map((run) => run.id)));
  const attachments = unique(state.turns.flatMap((turn) => turn.composerControls?.contextAttachmentKinds ?? []));
  const toolIntents = unique(state.turns.flatMap((turn) => turn.composerControls?.toolIntents ?? []));
  return <aside className="ps-rail" aria-label="Task context"><h3>Context</h3>
    <dl><dt>Task</dt><dd>{task?.title ?? 'No task selected'}</dd><dt>Task state</dt><dd>{task?.status ?? '—'}</dd><dt>Assistant session</dt><dd>{state.sessionId || 'Not started'}</dd><dt>Active turn</dt><dd>{state.activeTurnId ?? 'No active turn'}</dd><dt>Runtime state</dt><dd>{state.status.replace('_', ' ')}</dd><dt>Referenced artifacts</dt><dd>{state.referencedArtifacts.length}</dd></dl>
    <section><h4>Runs</h4>{runs.length ? <ul>{runs.map((runId) => <li key={runId}>{runId}</li>)}</ul> : <p className="ps-muted">No governed run references yet.</p>}</section>
    <section><h4>Approval</h4>{state.pendingApprovalId ? <p><a href="#/approvals">Open approval {state.pendingApprovalId}</a></p> : <p className="ps-muted">No pending approval.</p>}</section>
    <section><h4>Prompt context</h4>{attachments.length || toolIntents.length ? <ul>{attachments.map((item) => <li key={`attachment:${item}`}>attachment · {item}</li>)}{toolIntents.map((item) => <li key={`intent:${item}`}>safe intent · {item}</li>)}</ul> : <p className="ps-muted">No explicit safe prompt controls recorded.</p>}</section>
    <section><h4>Branch</h4><button type="button" disabled title="No governed branch context is available for this task.">Branch context unavailable</button></section>
  </aside>;
}
