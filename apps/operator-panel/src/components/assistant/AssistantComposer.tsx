import { useEffect, useState } from 'react';

import {
  validateAssistantRuntimeSettings,
  type AssistantRuntimeSettings,
} from '../../settings';
import { Button } from '../primitives/Button';
import { Icon } from '../primitives/Icon';

function runtimeDisplayLabel(settings: AssistantRuntimeSettings): string {
  const provider = settings.assistantProvider.trim() || 'profile default';
  const model = settings.assistantModel.trim() || settings.assistantHfModelId.trim() || 'profile default';
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
  onRuntimeSettingsChange,
  onSend,
}: {
  label: string;
  placeholder: string;
  sendLabel: string;
  disabled: boolean;
  initialValue?: string;
  statusLabel?: string;
  runtimeSettings: AssistantRuntimeSettings;
  onRuntimeSettingsChange: (next: Partial<AssistantRuntimeSettings>) => void;
  onSend: (message: string, runtimeSettings: AssistantRuntimeSettings) => void;
}) {
  const [draft, setDraft] = useState(initialValue);

  useEffect(() => {
    setDraft(initialValue);
  }, [initialValue]);

  const validationMessage = validateAssistantRuntimeSettings(runtimeSettings);
  const canSend = draft.trim().length > 0 && !disabled && !validationMessage;
  const visibleStatusLabel = statusLabel && statusLabel !== 'idle' ? statusLabel : '';
  const selectedRuntimeLabel = runtimeDisplayLabel(runtimeSettings);
  const sendDisabledReason =
    validationMessage ||
    (disabled
      ? 'Assistant is currently processing a turn.'
      : draft.trim().length === 0
        ? 'Enter a message to send.'
        : undefined);
  const updateRuntimeSetting = (key: keyof AssistantRuntimeSettings, value: string) => {
    onRuntimeSettingsChange({ [key]: value });
  };

  return (
    <form
      className="assistant-composer"
      aria-label="Assistant composer"
      onSubmit={(event) => {
        event.preventDefault();
        if (!canSend) {
          return;
        }
        onSend(draft, runtimeSettings);
        setDraft('');
      }}
    >
      <label className="assistant-composer-label" htmlFor="assistant-message">
        {label}
      </label>
      <textarea
        id="assistant-message"
        placeholder={placeholder}
        rows={3}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if ((event.metaKey || event.ctrlKey) && event.key === 'Enter' && canSend) {
            event.preventDefault();
            onSend(draft, runtimeSettings);
            setDraft('');
          }
        }}
      />
      <div className="assistant-runtime-settings" aria-label="Assistant runtime settings">
        <label>
          <span>Provider</span>
          <select
            aria-label="Assistant provider"
            value={runtimeSettings.assistantProvider}
            onChange={(event) => updateRuntimeSetting('assistantProvider', event.target.value)}
          >
            <option value="">Use profile default</option>
            <option value="auto">auto</option>
            <option value="ollama">ollama</option>
            <option value="transformers">transformers</option>
          </select>
        </label>
        <label>
          <span>Model</span>
          <input
            aria-label="Assistant model"
            value={runtimeSettings.assistantModel}
            onChange={(event) => updateRuntimeSetting('assistantModel', event.target.value)}
            placeholder="qwen3.5:4b"
          />
        </label>
        <label>
          <span>HF model id</span>
          <input
            aria-label="Assistant HF model id"
            value={runtimeSettings.assistantHfModelId}
            onChange={(event) => updateRuntimeSetting('assistantHfModelId', event.target.value)}
            placeholder="Qwen/Qwen2.5"
          />
        </label>
        <label>
          <span>Fallback</span>
          <select
            aria-label="Assistant fallback provider"
            value={runtimeSettings.assistantFallbackProvider}
            onChange={(event) => updateRuntimeSetting('assistantFallbackProvider', event.target.value)}
          >
            <option value="">Use profile default</option>
            <option value="transformers">transformers</option>
            <option value="ollama">ollama</option>
          </select>
        </label>
      </div>
      {validationMessage ? (
        <p className="assistant-runtime-validation" role="alert">
          {validationMessage}
        </p>
      ) : null}
      <div className="assistant-composer-actions">
        <div className="assistant-composer-tools">
          <button type="button" aria-label="Attach context" disabled title="Context attachment is not available yet">
            <Icon name="paperclip" />
          </button>
          <button type="button" disabled title="Tool selection is not available yet">
            <Icon name="command" />
            <span>Tools</span>
            <Icon name="chevron" />
          </button>
          {visibleStatusLabel ? <em>{visibleStatusLabel}</em> : null}
        </div>
        <div className="assistant-composer-submit">
          <span className="assistant-model-summary" aria-label="Selected assistant model">
            <span>Model</span>
            <strong>{selectedRuntimeLabel}</strong>
          </span>
          <Button
            type="submit"
            icon={<Icon name="arrow-up" />}
            variant="primary"
            disabled={!canSend}
            title={sendDisabledReason}
            data-disabled-reason={sendDisabledReason}
          >
            <span className="assistant-send-label">{sendLabel}</span>
          </Button>
        </div>
      </div>
    </form>
  );
}
