import type { ReactNode } from 'react';

import { StatusBadge } from '../primitives/Token';
import { operatorToneFromStatus, type OperatorTone } from './operatorPageUtils';

export type OperatorMetric = {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: OperatorTone;
};

export type OperatorDecisionItem = {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: OperatorTone;
};

export type OperatorPageAction = {
  label: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  title?: string;
  variant?: 'primary' | 'secondary' | 'danger';
};

export function OperatorPageShell({
  kicker,
  title,
  lead,
  status,
  statusTone,
  actions,
  decisionItems,
  metrics,
  children,
  context,
  className = '',
}: {
  kicker: string;
  title: string;
  lead?: ReactNode;
  status?: string;
  statusTone?: OperatorTone;
  actions?: OperatorPageAction[];
  decisionItems?: OperatorDecisionItem[];
  metrics?: OperatorMetric[];
  children: ReactNode;
  context?: ReactNode;
  className?: string;
}) {
  const visibleActions = actions?.filter(Boolean) ?? [];
  const visibleDecisionItems = decisionItems?.filter(Boolean) ?? [];
  const visibleMetrics = metrics?.filter(Boolean) ?? [];
  const pageClassName = ['workspace operator-page', context ? 'operator-page-with-context' : '', className]
    .filter(Boolean)
    .join(' ');

  return (
    <section className={pageClassName} data-testid="page-primary-region">
      <div className="workspace-header operator-page-header">
        <div>
          <p className="workspace-kicker">{kicker}</p>
          <div className="operator-page-title-row">
            <h2>{title}</h2>
            {status ? (
              <StatusBadge tone={statusTone ?? operatorToneFromStatus(status)} title={status}>
                {status}
              </StatusBadge>
            ) : null}
          </div>
          {lead ? <p className="workspace-lead">{lead}</p> : null}
        </div>
        {visibleActions.length > 0 ? (
          <div className="workspace-actions operator-page-actions">
            {visibleActions.map((action, index) => (
              <button
                key={index}
                className={
                  action.variant === 'primary'
                    ? 'action-btn'
                    : action.variant === 'danger'
                      ? 'action-btn action-danger'
                      : 'ghost-btn'
                }
                type="button"
                disabled={action.disabled}
                title={action.title}
                data-disabled-reason={action.disabled ? action.title : undefined}
                onClick={action.onClick}
              >
                {action.label}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      {visibleDecisionItems.length > 0 ? <OperatorDecisionStrip items={visibleDecisionItems} /> : null}
      {visibleMetrics.length > 0 ? <OperatorMetricStrip metrics={visibleMetrics} /> : null}

      <div className={context ? 'operator-page-layout' : 'operator-page-layout operator-page-layout-single'}>
        <div className="operator-page-main">{children}</div>
        {context ? <aside className="operator-page-context">{context}</aside> : null}
      </div>
    </section>
  );
}

export function OperatorDecisionStrip({ items }: { items: OperatorDecisionItem[] }) {
  return (
    <div className="operator-decision-strip" aria-label="Operator decision summary">
      {items.map((item) => (
        <article className="operator-decision-item" key={item.label}>
          <span>{item.label}</span>
          <strong>
            {typeof item.value === 'string' ? (
              <StatusBadge tone={item.tone ?? operatorToneFromStatus(item.value)} title={item.value}>
                {item.value}
              </StatusBadge>
            ) : (
              item.value
            )}
          </strong>
          {item.detail ? <p>{item.detail}</p> : null}
        </article>
      ))}
    </div>
  );
}

export function OperatorMetricStrip({ metrics }: { metrics: OperatorMetric[] }) {
  return (
    <div className="operator-metric-strip">
      {metrics.map((metric) => (
        <article className="operator-metric-card" key={metric.label}>
          <span>{metric.label}</span>
          <strong>{metric.value}</strong>
          {metric.detail ? <small>{metric.detail}</small> : null}
        </article>
      ))}
    </div>
  );
}
