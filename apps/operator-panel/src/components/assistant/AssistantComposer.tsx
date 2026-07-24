import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';

import {
  validateAssistantRuntimeSettings,
  type AssistantRuntimeSettings,
} from '../../settings';
import type { AssistantModelDiscoveryState } from '../../assistant/useAssistantModels';
import type {
  AssistantComposerControls,
  AssistantContextAttachmentKind,
  AssistantSafeToolIntent,
} from '../../assistant/assistantTypes';
import {
  assistantSlashCommands,
  hasAssistantSlashPrefix,
  resolveAssistantSlashCommand,
} from '../../assistant/assistantSlashCommands';
import { assistantUiText, translateAssistantText, type UiLocale } from '../../i18n';
import { Button } from '../primitives/Button';
import { Icon } from '../primitives/Icon';
import { AssistantModelPicker } from './AssistantModelPicker';

function runtimeDisplayLabel(settings: AssistantRuntimeSettings, locale: UiLocale): string {
  const defaultLabel = locale === 'tr' ? 'profil varsayılanı' : 'profile default';
  const provider = settings.assistantProvider.trim() || defaultLabel;
  const model = settings.assistantModel.trim() || settings.assistantHfModelId.trim() || defaultLabel;
  return `${provider} / ${model}`;
}

export function AssistantComposer({
  label,
  placeholder,
  sendLabel,
  disabled,
  initialValue = '',
  statusLabel = '',
  runtimeSettings,
  modelDiscovery,
  locale = 'en',
  onRuntimeSettingsChange,
  onSend,
  onCancel,
}: {
  label: string;
  placeholder: string;
  sendLabel: string;
  disabled: boolean;
  initialValue?: string;
  statusLabel?: string;
  runtimeSettings: AssistantRuntimeSettings;
  modelDiscovery?: AssistantModelDiscoveryState | null;
  locale?: UiLocale;
  onRuntimeSettingsChange: (next: Partial<AssistantRuntimeSettings>) => void;
  onSend: (
    message: string,
    runtimeSettings: AssistantRuntimeSettings,
    controls: AssistantComposerControls,
  ) => void;
  onCancel?: () => void;
}) {
  const text = assistantUiText[locale];
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const contextOptions: Array<{ kind: AssistantContextAttachmentKind; label: string }> = [
    { kind: 'active_run', label: text.activeRun },
    { kind: 'event_tail', label: text.recentEvents },
    { kind: 'approval_summary', label: text.approval },
    { kind: 'artifact_summary', label: text.artifacts },
    { kind: 'system_health', label: text.systemHealthAttachment },
  ];
  const toolOptions: Array<{ intent: AssistantSafeToolIntent; label: string }> = [
    { intent: 'inspect_run', label: text.inspectRun },
    { intent: 'summarize_events', label: text.summarizeEvents },
    { intent: 'explain_policy_blocker', label: text.explainBlocker },
    { intent: 'draft_remediation_plan', label: text.draftPlan },
    { intent: 'prepare_approval_review', label: text.prepareApprovalReview },
  ];
  const [draft, setDraft] = useState(initialValue);
  const [contextAttachmentKinds, setContextAttachmentKinds] = useState<AssistantContextAttachmentKind[]>(
    contextOptions.map((option) => option.kind),
  );
  const [toolIntents, setToolIntents] = useState<AssistantSafeToolIntent[]>(['inspect_run']);

  useEffect(() => {
    setDraft(initialValue);
  }, [initialValue]);

  const resizeDraft = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
  }, []);

  useLayoutEffect(() => {
    resizeDraft();
  }, [draft, resizeDraft]);

  const validationMessage = validateAssistantRuntimeSettings(runtimeSettings);
  const slashCommand = resolveAssistantSlashCommand(draft);
  const unsupportedSlashCommand = hasAssistantSlashPrefix(draft) && !slashCommand;
  const slashValidationMessage = unsupportedSlashCommand
    ? 'This slash command is not available in the governed assistant.'
    : slashCommand && !slashCommand.message
      ? 'Add a request after the slash command.'
      : undefined;
  const messageToSend = slashCommand ? slashCommand.message : draft;
  const mergedContextAttachmentKinds = Array.from(new Set([
    ...contextAttachmentKinds,
    ...(slashCommand?.contextAttachmentKinds ?? []),
  ]));
  const mergedToolIntents = Array.from(new Set([
    ...toolIntents,
    ...(slashCommand?.toolIntents ?? []),
  ]));
  const canSend = messageToSend.trim().length > 0 && !disabled && !validationMessage && !slashValidationMessage;
  const canCancel = disabled && Boolean(onCancel);
  const cancelLabel = locale === 'tr' ? 'Durdur' : 'Stop';
  const visibleStatusLabel = statusLabel && statusLabel !== 'idle' ? statusLabel : '';
  const selectedRuntimeLabel = runtimeDisplayLabel(runtimeSettings, locale);
  const controls: AssistantComposerControls = {
    contextAttachmentKinds: mergedContextAttachmentKinds,
    toolIntents: mergedToolIntents,
  };
  const sendDisabledReason =
    translateAssistantText(validationMessage, locale) ||
    slashValidationMessage ||
    (disabled
      ? translateAssistantText('Assistant is currently processing a turn.', locale)
        : messageToSend.trim().length === 0
        ? translateAssistantText('Enter a message to send.', locale)
        : undefined);
  const composerDisabledReason = disabled
    ? translateAssistantText('Assistant is currently processing a turn.', locale)
    : undefined;

  const toggleContext = (kind: AssistantContextAttachmentKind) => {
    setContextAttachmentKinds((previous) =>
      previous.includes(kind) ? previous.filter((item) => item !== kind) : [...previous, kind],
    );
  };
  const toggleTool = (intent: AssistantSafeToolIntent) => {
    setToolIntents((previous) =>
      previous.includes(intent) ? previous.filter((item) => item !== intent) : [...previous, intent],
    );
  };
  const submitDraft = () => {
    if (!canSend) {
      return;
    }
    onSend(messageToSend, runtimeSettings, controls);
    setDraft('');
  };

  return (
    <form
      className="assistant-composer"
      aria-label="Assistant composer"
      onSubmit={(event) => {
        event.preventDefault();
        submitDraft();
      }}
    >
      <label className="assistant-composer-label" htmlFor="assistant-message">
        {label}
      </label>
      <textarea
        ref={textareaRef}
        id="assistant-message"
        placeholder={placeholder}
        rows={3}
        value={draft}
        disabled={disabled}
        title={composerDisabledReason}
        data-disabled-reason={composerDisabledReason}
        onChange={(event) => {
          setDraft(event.target.value);
          if (typeof window !== 'undefined') {
            window.requestAnimationFrame(resizeDraft);
          }
        }}
        onKeyDown={(event) => {
          if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing) {
            return;
          }
          event.preventDefault();
          submitDraft();
        }}
      />
      <AssistantModelPicker
        runtimeSettings={runtimeSettings}
        modelDiscovery={modelDiscovery}
        locale={locale}
        onRuntimeSettingsChange={onRuntimeSettingsChange}
      />
      <div className="assistant-runtime-profiles" aria-label="Assistant runtime profiles">
        <label>Reasoning effort<select aria-label="Reasoning effort" value={runtimeSettings.reasoningEffort ?? 'medium'} onChange={(event) => onRuntimeSettingsChange({ reasoningEffort: event.target.value as NonNullable<AssistantRuntimeSettings['reasoningEffort']> })}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="very_high">Very high</option></select></label>
        <label>Speed<select aria-label="Speed profile" value={runtimeSettings.speedProfile ?? 'standard'} onChange={(event) => onRuntimeSettingsChange({ speedProfile: event.target.value as NonNullable<AssistantRuntimeSettings['speedProfile']> })}><option value="standard">Standard</option><option value="fast">Fast</option></select></label>
        <label>Approval<select aria-label="Approval profile" value={runtimeSettings.approvalProfile ?? 'risk_based'} onChange={(event) => onRuntimeSettingsChange({ approvalProfile: event.target.value as NonNullable<AssistantRuntimeSettings['approvalProfile']> })}><option value="always_ask">Always ask</option><option value="risk_based">Risk based</option><option value="policy_automatic">Within policy boundaries</option></select></label>
      </div>
      {validationMessage ? (
        <p className="assistant-runtime-validation" role="alert">
          {translateAssistantText(validationMessage, locale)}
        </p>
      ) : null}
      <div className="assistant-composer-actions">
        <div className="assistant-composer-tools">
          <details className="assistant-composer-menu">
            <summary aria-label={text.attachContext}>
              <Icon name="paperclip" />
              <span className="sr-only">{text.attachContext}</span>
            </summary>
            <div className="assistant-composer-menu-panel" role="group" aria-label={text.contextAttachments}>
              {contextOptions.map((option) => (
                <label key={option.kind}>
                  <input
                    type="checkbox"
                    checked={contextAttachmentKinds.includes(option.kind)}
                    onChange={() => toggleContext(option.kind)}
                  />
                  <span>{option.label}</span>
                </label>
              ))}
            </div>
          </details>
          <details className="assistant-composer-menu">
            <summary>Slash commands</summary>
            <div className="assistant-composer-menu-panel" role="group" aria-label="Governed slash commands">
              {assistantSlashCommands.map((command) => (
                <button key={command.command} type="button" onClick={() => setDraft(`${command.command} `)} title={command.description}>
                  <code>{command.command}</code><span>{command.description}</span>
                </button>
              ))}
            </div>
          </details>
          <details className="assistant-composer-menu">
            <summary>
              <Icon name="command" />
              <span>{text.tools}</span>
              <Icon name="chevron" />
            </summary>
            <div className="assistant-composer-menu-panel" role="group" aria-label={text.safeToolIntents}>
              {toolOptions.map((option) => (
                <label key={option.intent}>
                  <input
                    type="checkbox"
                    checked={toolIntents.includes(option.intent)}
                    onChange={() => toggleTool(option.intent)}
                  />
                  <span>{option.label}</span>
                </label>
              ))}
            </div>
          </details>
          {visibleStatusLabel ? <em>{visibleStatusLabel}</em> : null}
        </div>
        <div className="assistant-composer-submit">
          <span className="assistant-model-summary" aria-label={text.selectedAssistantModel}>
            <span>{text.model}</span>
            <strong>{selectedRuntimeLabel}</strong>
          </span>
          <Button
            type={canCancel ? 'button' : 'submit'}
            icon={<Icon name={canCancel ? 'close' : 'arrow-up'} />}
            variant="primary"
            disabled={canCancel ? false : !canSend}
            title={canCancel ? cancelLabel : sendDisabledReason}
            data-disabled-reason={canCancel ? undefined : sendDisabledReason}
            onClick={canCancel ? onCancel : undefined}
          >
            <span className="assistant-send-label">{canCancel ? cancelLabel : sendLabel}</span>
          </Button>
        </div>
      </div>
    </form>
  );
}
