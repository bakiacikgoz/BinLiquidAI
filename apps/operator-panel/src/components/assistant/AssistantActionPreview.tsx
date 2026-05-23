import type { AssistantProposedAction } from '../../assistant/assistantTypes';
import { Badge } from '../primitives/Badge';
import { Card } from '../primitives/Card';
import { Icon } from '../primitives/Icon';

function riskTone(risk: AssistantProposedAction['risk']): 'success' | 'warning' | 'error' {
  if (risk === 'low') {
    return 'success';
  }
  if (risk === 'high') {
    return 'error';
  }
  return 'warning';
}

export function AssistantActionPreview({ action }: { action: AssistantProposedAction }) {
  const copyCommand = () => {
    if (action.commandPreview) {
      void navigator.clipboard?.writeText(action.commandPreview);
    }
  };

  return (
    <Card className="assistant-action-preview">
      <div className="assistant-card-head">
        <span className="assistant-card-label">Proposed action</span>
        <Badge tone={riskTone(action.risk)}>{action.risk}</Badge>
      </div>
      <div className="assistant-action-title">
        <Icon name="approval" />
        <span>
          <strong>{action.title}</strong>
          <em>{action.target}</em>
        </span>
      </div>
      {action.commandPreview ? (
        <div className="assistant-command-preview">
          <code>{action.commandPreview}</code>
          <button type="button" onClick={copyCommand}>
            <Icon name="copy" /> Copy
          </button>
        </div>
      ) : null}
      <dl className="assistant-action-metrics">
        <div>
          <dt>Action Type</dt>
          <dd>{action.title}</dd>
        </div>
        <div>
          <dt>Target</dt>
          <dd>{action.target}</dd>
        </div>
        <div>
          <dt>Risk Level</dt>
          <dd>{action.risk}</dd>
        </div>
        <div>
          <dt>Dry Run</dt>
          <dd>Safe</dd>
        </div>
      </dl>
      <p>{action.dryRunSummary}</p>
    </Card>
  );
}
