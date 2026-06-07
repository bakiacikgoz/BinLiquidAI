import type { AssistantProposedAction } from '../../assistant/assistantTypes';
import { assistantUiText, translateAssistantText, type UiLocale } from '../../i18n';
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

export function AssistantActionPreview({ action, locale = 'en' }: { action: AssistantProposedAction; locale?: UiLocale }) {
  const text = assistantUiText[locale];
  const copyCommand = () => {
    if (action.commandPreview) {
      void navigator.clipboard?.writeText(action.commandPreview);
    }
  };

  return (
    <Card className="assistant-action-preview">
      <div className="assistant-card-head">
        <span className="assistant-card-label">{text.proposedAction}</span>
        <Badge tone={riskTone(action.risk)}>{translateAssistantText(action.risk, locale)}</Badge>
      </div>
      <div className="assistant-action-title">
        <Icon name="approval" />
        <span>
          <strong>{translateAssistantText(action.title, locale)}</strong>
          <em>{translateAssistantText(action.target, locale)}</em>
        </span>
      </div>
      {action.commandPreview ? (
        <div className="assistant-command-preview">
          <code>{action.commandPreview}</code>
          <button type="button" onClick={copyCommand}>
            <Icon name="copy" /> {text.copy}
          </button>
        </div>
      ) : null}
      <dl className="assistant-action-metrics">
        <div>
          <dt>{text.actionType}</dt>
          <dd>{translateAssistantText(action.title, locale)}</dd>
        </div>
        <div>
          <dt>{text.target}</dt>
          <dd>{translateAssistantText(action.target, locale)}</dd>
        </div>
        <div>
          <dt>{text.riskLevel}</dt>
          <dd>{translateAssistantText(action.risk, locale)}</dd>
        </div>
        <div>
          <dt>{text.dryRun}</dt>
          <dd>{text.safe}</dd>
        </div>
      </dl>
      <p>{translateAssistantText(action.dryRunSummary, locale)}</p>
    </Card>
  );
}
