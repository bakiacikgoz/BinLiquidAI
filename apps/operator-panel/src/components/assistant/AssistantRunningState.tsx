import type { AssistantTimelineItem, AssistantTurnStatus } from '../../assistant/assistantTypes';
import { Badge } from '../primitives/Badge';
import { StatusDot } from '../primitives/StatusDot';

function statusTone(status: AssistantTurnStatus): 'success' | 'warning' | 'error' | 'info' | 'neutral' {
  if (status === 'completed') {
    return 'success';
  }
  if (status === 'awaiting_approval') {
    return 'warning';
  }
  if (status === 'failed' || status === 'cancelled') {
    return 'error';
  }
  if (status === 'idle') {
    return 'neutral';
  }
  return 'info';
}

function dotTone(tone: ReturnType<typeof statusTone>): 'success' | 'warning' | 'error' | 'info' | 'muted' {
  return tone === 'neutral' ? 'muted' : tone;
}

export function AssistantRunningState({
  status,
  timeline,
}: {
  status: AssistantTurnStatus;
  timeline: AssistantTimelineItem[];
}) {
  const tone = statusTone(status);
  return (
    <div className="assistant-running-state">
      <Badge tone={tone}>
        <StatusDot tone={dotTone(tone)} pulse={status === 'starting' || status === 'streaming'} /> {status}
      </Badge>
      {timeline.length > 0 ? (
        <div className="assistant-activity-list">
          {timeline.slice(-5).map((item) => (
            <div className="assistant-activity-row" key={item.id}>
              <StatusDot tone={item.tone} />
              <span>
                <strong>{item.title}</strong>
                <em>{item.subtitle}</em>
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
