import type { AssistantTaskSubmissionResult } from '../../assistant/assistantTaskingTypes';
import { Badge, type BadgeTone } from '../primitives/Badge';
import { Card } from '../primitives/Card';
import { Icon } from '../primitives/Icon';

function statusTone(status: AssistantTaskSubmissionResult['status']): BadgeTone {
  if (status === 'accepted') {
    return 'success';
  }
  if (status === 'denied' || status === 'invalid_request' || status === 'unknown_agent') {
    return 'error';
  }
  return 'warning';
}

export function AssistantTaskSubmitResult({ submission }: { submission: AssistantTaskSubmissionResult }) {
  return (
    <Card className="assistant-task-submit-card">
      <div className="assistant-card-head">
        <span className="assistant-card-label">Task submission</span>
        <Badge tone={statusTone(submission.status)}>{submission.status.replaceAll('_', ' ')}</Badge>
      </div>
      <div className="assistant-task-title">
        <Icon name="send" />
        <span>
          <strong>{submission.reasonCode}</strong>
          <em>{submission.proposalId}</em>
        </span>
      </div>
      <dl className="assistant-task-metrics">
        <div>
          <dt>Policy</dt>
          <dd>{submission.policyDecision.replaceAll('_', ' ')}</dd>
        </div>
        <div>
          <dt>Run</dt>
          <dd>{submission.runId ?? 'not created'}</dd>
        </div>
        <div>
          <dt>Approval</dt>
          <dd>{submission.approvalId ?? 'not required'}</dd>
        </div>
      </dl>
      {submission.nextActions.length > 0 ? (
        <ul className="assistant-task-next-actions">
          {submission.nextActions.map((action) => (
            <li key={action}>{action}</li>
          ))}
        </ul>
      ) : null}
    </Card>
  );
}
