import type { AssistantApprovalSummary } from '../../assistant/assistantTypes';
import { Badge } from '../primitives/Badge';
import { Button } from '../primitives/Button';
import { Card } from '../primitives/Card';
import { Icon } from '../primitives/Icon';
import { StatusDot } from '../primitives/StatusDot';

function approvalTone(risk: AssistantApprovalSummary['risk']): 'warning' | 'error' | 'info' {
  if (risk === 'high') {
    return 'error';
  }
  if (risk === 'medium') {
    return 'warning';
  }
  return 'info';
}

export function AssistantApprovalCard({
  approval,
  disabled,
  disabledReason,
  onReview,
  onApprove,
  onReject,
  onExecute,
}: {
  approval: AssistantApprovalSummary;
  disabled: boolean;
  disabledReason: string;
  onReview: (approvalId: string) => void;
  onApprove: (approvalId: string) => void;
  onReject: (approvalId: string) => void;
  onExecute: (approvalId: string) => void;
}) {
  const approved = approval.status === 'approved';
  return (
    <Card className="assistant-approval-card">
      <div className="assistant-card-head">
        <span className="assistant-card-label">Approval required</span>
        <Badge tone={approvalTone(approval.risk)}>
          <StatusDot tone={approvalTone(approval.risk)} /> {approval.status}
        </Badge>
      </div>
      <div className="assistant-approval-body">
        <span className="assistant-approval-icon">
          <Icon name="shield" />
        </span>
        <div>
          <strong>{approval.title}</strong>
          <p>{approval.approvalId}</p>
        </div>
      </div>
      {!approval.detailLoaded ? <p className="assistant-warning-text">Approval detail is loading.</p> : null}
      {disabled ? <p className="assistant-warning-text">{disabledReason}</p> : null}
      <div className="assistant-approval-actions">
        <Button icon={<Icon name="eye" />} variant="secondary" onClick={() => onReview(approval.approvalId)}>
          Review Details
        </Button>
        <Button
          disabled={disabled || approved}
          icon={<Icon name="check" />}
          variant="primary"
          onClick={() => onApprove(approval.approvalId)}
        >
          Approve
        </Button>
        <Button
          disabled={disabled}
          icon={<Icon name="reject" />}
          variant="danger"
          onClick={() => onReject(approval.approvalId)}
        >
          Reject
        </Button>
        <Button
          disabled={disabled || !approved}
          icon={<Icon name="play" />}
          variant="secondary"
          onClick={() => onExecute(approval.approvalId)}
        >
          Execute
        </Button>
      </div>
    </Card>
  );
}
