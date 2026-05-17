import type { AssistantArtifactRef, AssistantRunRef } from '../../assistant/assistantTypes';
import { Badge } from '../primitives/Badge';
import { Card } from '../primitives/Card';
import { StatusDot } from '../primitives/StatusDot';

export function AssistantRunReferences({
  runs,
  artifacts,
  emptyRunLabel,
}: {
  runs: AssistantRunRef[];
  artifacts: AssistantArtifactRef[];
  emptyRunLabel: string;
}) {
  return (
    <Card className="assistant-reference-card">
      <div className="assistant-card-head">
        <span className="assistant-card-label">References</span>
        <Badge tone={runs.length > 0 || artifacts.length > 0 ? 'info' : 'neutral'}>
          {runs.length + artifacts.length}
        </Badge>
      </div>
      <div className="assistant-reference-list">
        {runs.length === 0 && artifacts.length === 0 ? <p>{emptyRunLabel}</p> : null}
        {runs.map((run) => (
          <div className="assistant-reference-row" key={run.id}>
            <StatusDot tone={run.status === 'blocked' ? 'warning' : 'info'} />
            <span>
              <strong>{run.id}</strong>
              <em>{run.summary || run.status || 'Referenced run'}</em>
            </span>
          </div>
        ))}
        {artifacts.map((artifact) => (
          <div className="assistant-reference-row" key={`${artifact.name}-${artifact.path ?? ''}`}>
            <StatusDot tone="success" />
            <span>
              <strong>{artifact.name}</strong>
              <em>{artifact.summary || artifact.path || 'Referenced artifact'}</em>
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}
