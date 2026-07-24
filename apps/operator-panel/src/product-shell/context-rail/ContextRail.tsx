import type { ProductTask } from '../state/productShellStore';

export function ContextRail({ task }: { task?: ProductTask }) {
  return <aside className="ps-rail" aria-label="Task context"><h3>Context</h3>
    <dl><dt>Task</dt><dd>{task?.title ?? 'No task selected'}</dd><dt>State</dt><dd>{task?.status ?? '—'}</dd><dt>Safety</dt><dd>Policy and approvals apply</dd></dl>
  </aside>;
}
