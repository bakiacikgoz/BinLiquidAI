import type { ReactNode } from 'react';

export function SectionHeader({
  title,
  action,
}: {
  title: string;
  action?: ReactNode;
}) {
  return (
    <div className="mc-section-header">
      <h3>{title}</h3>
      {action ? <div className="mc-section-action">{action}</div> : null}
    </div>
  );
}
