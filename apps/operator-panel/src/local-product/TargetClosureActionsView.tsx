import { mapTargetClosureActions } from './platformEvidenceHarvestMappers';

export function TargetClosureActionsView({ actions }: { actions: unknown }) {
  const vm = mapTargetClosureActions(actions);
  return (
    <section className="workspace" data-testid="target-closure-actions-view">
      <div className="workspace-header">
        <div>
          <p className="eyebrow">Target Closure</p>
          <h2>Missing Target Actions</h2>
        </div>
        <span className="status-pill status-warn">{vm.length}</span>
      </div>
      <div className="table-shell">
        <table>
          <thead>
            <tr>
              <th>Target</th>
              <th>Path</th>
              <th>Command</th>
              <th>Runbook</th>
            </tr>
          </thead>
          <tbody>
            {vm.map((action) => (
              <tr key={action.target}>
                <td>{action.target}</td>
                <td>{action.recommendedPath}</td>
                <td>{action.commands[0] ?? 'none'}</td>
                <td>{action.runbook}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

