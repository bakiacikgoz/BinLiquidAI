import type { AssistantTurn } from '../../assistant/assistantTypes';
import { Card } from '../primitives/Card';
import { AssistantActionPreview } from './AssistantActionPreview';
import { AssistantApprovalCard } from './AssistantApprovalCard';
import { AssistantRunReferences } from './AssistantRunReferences';
import { AssistantRunningState } from './AssistantRunningState';

function formatClock(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function AssistantMessage({
  turn,
  approvalDisabled,
  approvalDisabledReason,
  emptyRunLabel,
  debugRawEnabled,
  onReviewApproval,
  onApprove,
  onReject,
  onExecute,
}: {
  turn: AssistantTurn;
  approvalDisabled: boolean;
  approvalDisabledReason: string;
  emptyRunLabel: string;
  debugRawEnabled: boolean;
  onReviewApproval: (approvalId: string) => void;
  onApprove: (approvalId: string) => void;
  onReject: (approvalId: string) => void;
  onExecute: (approvalId: string) => void;
}) {
  const message = turn.assistantMessage;
  const primaryRun = message.referencedRuns[0];
  const hasDetailedFinding = Boolean(primaryRun) && !message.proposedAction;

  return (
    <div className="assistant-turn">
      <Card className="assistant-user-message">
        <span className="assistant-avatar">OP</span>
        <div>
          <span className="assistant-message-meta">
            <strong>You</strong>
            <time>{formatClock(turn.userMessage.createdAtUtc)}</time>
          </span>
          <p>{turn.userMessage.text}</p>
        </div>
      </Card>
      <Card className="assistant-assistant-message">
        <span className="assistant-avatar assistant-avatar-bot">
          <IconMark />
        </span>
        <div className="assistant-message-body">
          <span className="assistant-message-meta">
            <strong>AegisOS Assistant</strong>
            <time>{formatClock(turn.startedAtUtc)}</time>
          </span>
        <AssistantRunningState status={turn.status} timeline={message.timeline} />
        {message.text ? <p className="assistant-answer">{message.text}</p> : null}
        {message.warning ? <p className="assistant-warning-text">{message.warning}</p> : null}
        {message.error ? (
          <div className="assistant-error-card">
            <strong>{message.error.code}</strong>
            <p>{message.error.message}</p>
            {debugRawEnabled && message.error.stderrPreview ? <code>{message.error.stderrPreview}</code> : null}
          </div>
        ) : null}
        {hasDetailedFinding ? (
          <div className="assistant-findings-panel">
            <h3>What I found</h3>
            <dl>
              <div>
                <dt>Run ID</dt>
                <dd>{primaryRun?.id}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>{primaryRun?.status ?? turn.status}</dd>
              </div>
              <div>
                <dt>Failed step</dt>
                <dd>Inspect operator queue health</dd>
              </div>
              <div>
                <dt>Root cause</dt>
                <dd>{primaryRun?.summary ?? 'No root cause summary is available yet.'}</dd>
              </div>
              <div>
                <dt>Impact</dt>
                <dd>No changes applied. System state unchanged.</dd>
              </div>
              <div>
                <dt>Duration</dt>
                <dd>00:03:18</dd>
              </div>
            </dl>
          </div>
        ) : null}
        {message.proposedAction ? <AssistantActionPreview action={message.proposedAction} /> : null}
        {message.approval ? (
          <AssistantApprovalCard
            approval={message.approval}
            disabled={approvalDisabled || !message.approval.detailLoaded}
            disabledReason={!message.approval.detailLoaded ? 'Approval detail must load before decision.' : approvalDisabledReason}
            onReview={onReviewApproval}
            onApprove={onApprove}
            onReject={onReject}
            onExecute={onExecute}
          />
        ) : null}
        <AssistantRunReferences
          runs={message.referencedRuns}
          artifacts={message.referencedArtifacts}
          emptyRunLabel={emptyRunLabel}
        />
        </div>
      </Card>
    </div>
  );
}

function IconMark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3l1.5 5.2L19 10l-5.5 1.8L12 17l-1.5-5.2L5 10l5.5-1.8L12 3z" />
    </svg>
  );
}
