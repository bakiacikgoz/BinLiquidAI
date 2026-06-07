import type { AssistantApprovalSummary } from '../../assistant/assistantTypes';
import { assistantUiText, translateAssistantText, type UiLocale } from '../../i18n';
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
  locale = 'en',
  onReview,
  onApprove,
  onReject,
  onExecute,
}: {
  approval: AssistantApprovalSummary;
  disabled: boolean;
  disabledReason: string;
  locale?: UiLocale;
  onReview: (approvalId: string) => void;
  onApprove: (approvalId: string) => void;
  onReject: (approvalId: string) => void;
  onExecute: (approvalId: string) => void;
}) {
  const text = assistantUiText[locale];
  const approved = approval.status === 'approved';
  const disabledActionReason = disabled ? disabledReason : '';
  const approveDisabledReason = approved ? translateAssistantText('Approval is already approved.', locale) : disabledActionReason;
  const executeDisabledReason = approved
    ? disabledActionReason
    : translateAssistantText('Approval must be approved before execution.', locale);
  return (
    <Card className="assistant-approval-card">
      <div className="assistant-card-head">
        <span className="assistant-card-label">{text.approvalRequired}</span>
        <Badge tone={approvalTone(approval.risk)}>
          <StatusDot tone={approvalTone(approval.risk)} /> {translateAssistantText(approval.status, locale)}
        </Badge>
      </div>
      <div className="assistant-approval-body">
        <span className="assistant-approval-icon">
          <Icon name="shield" />
        </span>
        <div>
          <strong>{translateAssistantText(approval.title, locale)}</strong>
          <p>{approval.approvalId}</p>
        </div>
      </div>
      {!approval.detailLoaded ? (
        <p className="assistant-warning-text">{translateAssistantText('Approval detail is loading.', locale)}</p>
      ) : null}
      {disabled ? <p className="assistant-warning-text">{disabledReason}</p> : null}
      <div className="assistant-approval-actions">
        <Button icon={<Icon name="eye" />} variant="secondary" onClick={() => onReview(approval.approvalId)}>
          {text.reviewDetails}
        </Button>
        <Button
          disabled={disabled || approved}
          title={approveDisabledReason || undefined}
          data-disabled-reason={approveDisabledReason || undefined}
          icon={<Icon name="check" />}
          variant="primary"
          onClick={() => onApprove(approval.approvalId)}
        >
          {text.approve}
        </Button>
        <Button
          disabled={disabled}
          title={disabledActionReason || undefined}
          data-disabled-reason={disabledActionReason || undefined}
          icon={<Icon name="reject" />}
          variant="danger"
          onClick={() => onReject(approval.approvalId)}
        >
          {text.reject}
        </Button>
        <Button
          disabled={disabled || !approved}
          title={executeDisabledReason || undefined}
          data-disabled-reason={executeDisabledReason || undefined}
          icon={<Icon name="play" />}
          variant="secondary"
          onClick={() => onExecute(approval.approvalId)}
        >
          {text.execute}
        </Button>
      </div>
    </Card>
  );
}
