import type { SystemHealthSummary } from '../shell/RightRail';
import { Badge } from '../primitives/Badge';
import { Card } from '../primitives/Card';
import { StatusDot } from '../primitives/StatusDot';

function healthTone(health: SystemHealthSummary['health']): 'success' | 'warning' | 'error' | 'info' {
  if (health === 'Healthy') {
    return 'success';
  }
  if (health === 'Blocked') {
    return 'error';
  }
  if (health === 'Degraded') {
    return 'warning';
  }
  return 'info';
}

export function AssistantSystemHealthCard({
  title,
  systemHealth,
}: {
  title: string;
  systemHealth: SystemHealthSummary;
}) {
  const tone = healthTone(systemHealth.health);
  return (
    <Card className="assistant-system-health-card">
      <div className="assistant-card-head">
        <span className="assistant-card-label">{title}</span>
        <Badge tone={tone}>
          <StatusDot tone={tone} /> {systemHealth.health}
        </Badge>
      </div>
      <dl className="assistant-rail-dl">
        <div>
          <dt>Mode</dt>
          <dd>{systemHealth.coreMode || '-'}</dd>
        </div>
        <div>
          <dt>Contract</dt>
          <dd>{systemHealth.contractVersion}</dd>
        </div>
      </dl>
    </Card>
  );
}
