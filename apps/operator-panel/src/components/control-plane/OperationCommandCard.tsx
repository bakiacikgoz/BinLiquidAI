import { getReasonCodeMessage } from '../../control-plane/reasonCodes';
import type { OperationDescriptor } from '../../control-plane/types';
import type { UiLocale } from '../../i18n';

type OperationCommandListProps = {
  operations: OperationDescriptor[];
  categories: OperationDescriptor['category'][];
  emptyMessage: string;
  locale: UiLocale;
};

export function OperationCommandList({ operations, categories, emptyMessage, locale }: OperationCommandListProps) {
  const visibleOperations = operations.filter((operation) => categories.includes(operation.category));

  if (visibleOperations.length === 0) {
    return <p className="supporting">{emptyMessage}</p>;
  }

  return (
    <div className="operation-command-list">
      {visibleOperations.map((operation) => (
        <OperationCommandCard operation={operation} locale={locale} key={operation.operationId} />
      ))}
    </div>
  );
}

export function OperationCommandCard({ operation, locale }: { operation: OperationDescriptor; locale: UiLocale }) {
  const lastResult = operation.lastResult;
  const actionState = operation.enabled
    ? 'enabled'
    : operation.disabledReason
      ? getReasonCodeMessage(operation.disabledReason, locale)
      : 'disabled';

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
          <dd>{actionState}</dd>
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
