import type { AssistantTurn } from '../../assistant/assistantTypes';
import { assistantUiText, translateAssistantText, type UiLocale } from '../../i18n';
import { Card } from '../primitives/Card';
import { Icon } from '../primitives/Icon';
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
  locale = 'en',
  onReviewApproval,
  onApprove,
  onReject,
  onExecute,
  onRegenerate,
}: {
  turn: AssistantTurn;
  approvalDisabled: boolean;
  approvalDisabledReason: string;
  emptyRunLabel: string;
  debugRawEnabled: boolean;
  locale?: UiLocale;
  onReviewApproval: (approvalId: string) => void;
  onApprove: (approvalId: string) => void;
  onReject: (approvalId: string) => void;
  onExecute: (approvalId: string) => void;
  onRegenerate: (turnId: string) => void;
}) {
  const text = assistantUiText[locale];
  const message = turn.assistantMessage;
  const primaryRun = message.referencedRuns[0];
  const hasDetailedFinding = Boolean(primaryRun) && !message.proposedAction;
  const hasAssistantOutput = Boolean(
    message.text ||
      message.warning ||
      message.error ||
      message.proposedAction ||
      message.approval ||
      message.referencedRuns.length > 0 ||
      message.referencedArtifacts.length > 0,
  );
  const copyAssistantText = () => {
    if (message.text && typeof navigator !== 'undefined' && navigator.clipboard) {
      void navigator.clipboard.writeText(message.text);
    }
  };

  return (
    <div className="assistant-turn">
      <Card className="assistant-user-message">
        <div>
          <time className="assistant-user-time">{formatClock(turn.userMessage.createdAtUtc)}</time>
          <p>{turn.userMessage.text}</p>
        </div>
      </Card>
      <Card className="assistant-assistant-message">
        <div className="assistant-message-body">
          <span className="assistant-message-meta">
            <time>{formatClock(turn.startedAtUtc)}</time>
          </span>
        <AssistantRunningState
          status={turn.status}
          timeline={message.timeline}
          startedAtUtc={turn.startedAtUtc}
          completedAtUtc={turn.completedAtUtc}
          locale={locale}
        />
        {message.text ? <p className="assistant-answer">{translateAssistantText(message.text, locale)}</p> : null}
        {message.warning ? <p className="assistant-warning-text">{translateAssistantText(message.warning, locale)}</p> : null}
        {message.error ? (
          <div className="assistant-error-card">
            <strong>{message.error.code}</strong>
            <p>{translateAssistantText(message.error.message, locale)}</p>
            {debugRawEnabled && message.error.stderrPreview ? <code>{message.error.stderrPreview}</code> : null}
          </div>
        ) : null}
        {hasDetailedFinding ? (
          <div className="assistant-findings-panel">
            <h3>{text.whatIFound}</h3>
            <dl>
              <div>
                <dt>{text.runId}</dt>
                <dd>{primaryRun?.id}</dd>
              </div>
              <div>
                <dt>{text.status}</dt>
                <dd>{translateAssistantText(primaryRun?.status ?? turn.status, locale)}</dd>
              </div>
              <div>
                <dt>{text.failedStep}</dt>
                <dd>{locale === 'tr' ? 'Operatör kuyruğu sağlığını incele' : 'Inspect operator queue health'}</dd>
              </div>
              <div>
                <dt>{text.rootCause}</dt>
                <dd>{primaryRun?.summary ? translateAssistantText(primaryRun.summary, locale) : text.noRootCause}</dd>
              </div>
              <div>
                <dt>{text.impact}</dt>
                <dd>{text.noChanges}</dd>
              </div>
              <div>
                <dt>{text.duration}</dt>
                <dd>00:03:18</dd>
              </div>
            </dl>
          </div>
        ) : null}
        {message.proposedAction ? <AssistantActionPreview action={message.proposedAction} locale={locale} /> : null}
        {message.approval ? (
          <AssistantApprovalCard
            approval={message.approval}
            disabled={approvalDisabled || !message.approval.detailLoaded}
            disabledReason={
              !message.approval.detailLoaded
                ? translateAssistantText('Approval detail must load before decision.', locale)
                : translateAssistantText(approvalDisabledReason, locale)
            }
            locale={locale}
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
          locale={locale}
        />
        {hasAssistantOutput ? (
          <div className="assistant-message-actions" aria-label="Assistant message actions">
            <button type="button" aria-label={text.copyAnswer} title={text.copyAnswer} onClick={copyAssistantText}>
              <Icon name="copy" />
            </button>
            <button type="button" aria-label={text.regenerateAnswer} title={text.regenerateAnswer} onClick={() => onRegenerate(turn.id)}>
              <Icon name="refresh" />
            </button>
          </div>
        ) : null}
        </div>
      </Card>
    </div>
  );
}
