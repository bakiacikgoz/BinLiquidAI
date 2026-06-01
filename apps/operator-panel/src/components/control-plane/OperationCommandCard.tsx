import type { OperationDescriptor } from '../../control-plane/types';

type OperationCommandListProps = {
  operations: OperationDescriptor[];
  categories: OperationDescriptor['category'][];
  emptyMessage: string;
};

export function OperationCommandList({ operations, categories, emptyMessage }: OperationCommandListProps) {
  const visibleOperations = operations.filter((operation) => categories.includes(operation.category));

  if (visibleOperations.length === 0) {
    return <p className="supporting">{emptyMessage}</p>;
  }

  return (
    <div className="operation-command-list">
      {visibleOperations.map((operation) => (
        <OperationCommandCard operation={operation} key={operation.operationId} />
      ))}
    </div>
  );
}

export function OperationCommandCard({ operation }: { operation: OperationDescriptor }) {
  const lastResult = operation.lastResult;

  return (
    <article className="operation-command-card">
      <div>
        <strong>{operation.label}</strong>
        <span>{operation.description}</span>
      </div>
      <dl className="metric-list compact">
        <div className="metric-row">
          <dt>Operation</dt>
          <dd>{operation.operationId}</dd>
        </div>
        <div className="metric-row">
          <dt>Risk</dt>
          <dd>{operation.riskLevel}</dd>
        </div>
        <div className="metric-row">
          <dt>Permission</dt>
          <dd>{operation.permission}</dd>
        </div>
        <div className="metric-row">
          <dt>Dry-run</dt>
          <dd>{operation.supportsDryRun ? 'supported' : 'not supported'}</dd>
        </div>
        <div className="metric-row">
          <dt>Action state</dt>
          <dd>{operation.enabled ? 'enabled' : operation.disabledReason || 'disabled'}</dd>
        </div>
        {lastResult ? (
          <div className="metric-row">
            <dt>Last result</dt>
            <dd>{`${lastResult.status}: ${lastResult.summary}`}</dd>
          </div>
        ) : null}
      </dl>
    </article>
  );
}
