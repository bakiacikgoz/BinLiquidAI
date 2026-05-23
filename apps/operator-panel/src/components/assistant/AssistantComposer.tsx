import { useEffect, useState } from 'react';

import { Button } from '../primitives/Button';
import { Icon } from '../primitives/Icon';

export function AssistantComposer({
  label,
  placeholder,
  sendLabel,
  disabled,
  initialValue = '',
  statusLabel = '',
  onSend,
}: {
  label: string;
  placeholder: string;
  sendLabel: string;
  disabled: boolean;
  initialValue?: string;
  statusLabel?: string;
  onSend: (message: string) => void;
}) {
  const [draft, setDraft] = useState(initialValue);

  useEffect(() => {
    setDraft(initialValue);
  }, [initialValue]);

  const canSend = draft.trim().length > 0 && !disabled;
  const visibleStatusLabel = statusLabel && statusLabel !== 'idle' ? statusLabel : '';
  return (
    <form
      className="assistant-composer"
      aria-label="Assistant composer"
      onSubmit={(event) => {
        event.preventDefault();
        if (!canSend) {
          return;
        }
        onSend(draft);
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
            onSend(draft);
            setDraft('');
          }
        }}
      />
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
          <button
            type="button"
            className="assistant-model-select"
            aria-label="Assistant model"
            disabled
            title="Model selection is managed by settings"
          >
            <span>Model</span>
            <strong>AegisOS-Pro</strong>
            <Icon name="chevron" />
          </button>
          <Button type="submit" icon={<Icon name="arrow-up" />} variant="primary" disabled={!canSend}>
            <span className="assistant-send-label">{sendLabel}</span>
          </Button>
        </div>
      </div>
    </form>
  );
}
