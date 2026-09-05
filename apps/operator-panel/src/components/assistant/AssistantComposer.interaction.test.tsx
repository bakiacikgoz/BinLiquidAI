import { useState } from 'react';
import { act, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import {
  DEFAULT_ASSISTANT_RUNTIME_SETTINGS,
  type AssistantRuntimeSettings,
} from '../../settings';
import type { AssistantModelDiscoveryState } from '../../assistant/useAssistantModels';
import type { AssistantComposerControls } from '../../assistant/assistantTypes';
import { renderOperatorPanel } from '../../test/render';
import { AssistantComposer } from './AssistantComposer';

function ComposerHarness({
  onSend,
  modelDiscovery = null,
  variant = 'operator',
  locale = 'en',
}: {
  onSend: (
    message: string,
    runtimeSettings: AssistantRuntimeSettings,
    controls: AssistantComposerControls,
  ) => void;
  modelDiscovery?: AssistantModelDiscoveryState | null;
  variant?: 'operator' | 'product';
  locale?: 'en' | 'tr';
}) {
  const [runtimeSettings, setRuntimeSettings] = useState<AssistantRuntimeSettings>({
    ...DEFAULT_ASSISTANT_RUNTIME_SETTINGS,
  });

  return (
    <AssistantComposer
      label="Message"
      placeholder="Ask about systems"
      sendLabel="Send"
      disabled={false}
      runtimeSettings={runtimeSettings}
      modelDiscovery={modelDiscovery}
      variant={variant}
      locale={locale}
      onRuntimeSettingsChange={(next) => setRuntimeSettings((prev) => ({ ...prev, ...next }))}
      onSend={onSend}
    />
  );
}

const discoveredModels: AssistantModelDiscoveryState = {
  status: 'success',
  response: null,
  providers: [],
  models: [
    {
      provider: 'ollama',
      id: 'qwen3.5:4b',
      displayName: 'qwen3.5:4b',
      installed: true,
      configured: true,
      source: 'ollama',
      warnings: [],
    },
  ],
  error: null,
  refresh: vi.fn(),
};

describe('AssistantComposer runtime controls', () => {
  it('allows configured models from available providers without a local installation', async () => {
    const configured = { ...discoveredModels, models: [{ ...discoveredModels.models[0], provider: 'local-transformers', installed: false, configured: true }] };
    const { user } = renderOperatorPanel(<ComposerHarness onSend={vi.fn()} variant="product" modelDiscovery={configured} />);
    await user.click(screen.getByRole('button', { name: /profile default/i }));
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Choose model' }));
    expect(screen.getByRole('radio', { name: /qwen3.5:4b/ })).toBeEnabled();
  });
  it('selects a discovered model from the compact list and adjusts reasoning', async () => {
    const onSend = vi.fn();
    const { user } = renderOperatorPanel(<ComposerHarness onSend={onSend} variant="product" modelDiscovery={discoveredModels} />);
    await user.click(screen.getByRole('button', { name: /profile default/i }));
    await user.click(screen.getByRole('button', { name: 'Choose model' }));
    await user.click(screen.getByRole('radio', { name: /qwen3.5:4b/ }));
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Choose model' })).toHaveTextContent('qwen3.5:4b');
    const effort = screen.getByRole('slider', { name: 'Reasoning effort' });
    effort.focus();
    await user.keyboard('{ArrowRight}');
    await user.keyboard('{Escape}');
    await user.type(screen.getByLabelText('Message'), 'Hello');
    await user.click(screen.getByRole('button', { name: 'Send' }));
    expect(onSend).toHaveBeenCalledWith('Hello', expect.objectContaining({ assistantModel: 'qwen3.5:4b' }), expect.any(Object));
  });
  it('blocks duplicate pending sends and preserves a newly selected command draft', async () => {
    let finish!: () => void;
    const onSend = vi.fn(() => new Promise<void>((resolve) => { finish = resolve; }));
    const { user, container } = renderOperatorPanel(<ComposerHarness onSend={onSend} />);
    await user.type(screen.getByLabelText('Message'), 'Original request');
    await user.dblClick(screen.getByRole('button', { name: 'Send' }));
    expect(onSend).toHaveBeenCalledTimes(1);
    const command = container.querySelector<HTMLButtonElement>('.assistant-composer-menu-panel button')!;
    await user.click(command);
    const nextDraft = (screen.getByLabelText('Message') as HTMLTextAreaElement).value;
    expect(nextDraft).not.toBe('Original request');
    await act(async () => finish());
    expect(screen.getByLabelText('Message')).toHaveValue(nextDraft);
  });
  it('keeps the draft when sending fails', async () => {
    const { user } = renderOperatorPanel(<ComposerHarness onSend={async () => false} />);
    await user.type(screen.getByLabelText('Message'), 'Keep this request');
    await user.click(screen.getByRole('button', { name: 'Send' }));
    expect(screen.getByLabelText('Message')).toHaveValue('Keep this request');
  });

  it('opens model settings and dismisses them with Escape', async () => {
    const { user } = renderOperatorPanel(<ComposerHarness onSend={vi.fn()} variant="product" />);
    const trigger = screen.getByRole('button', { name: /profile default/i });
    await user.click(trigger);
    expect(screen.getByRole('dialog', { name: 'Model settings' })).toBeVisible();
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog', { name: 'Model settings' })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
  it('uses the UI Lab composer hierarchy for product surfaces', () => {
    const { container } = renderOperatorPanel(
      <ComposerHarness onSend={vi.fn()} variant="product" />,
    );

    expect(container.querySelector('.composer-stack.is-home')).toBeInTheDocument();
    expect(container.querySelector('form.composer.codex-composer.is-home')).toBeInTheDocument();
    expect(container.querySelector('.composer-context-bar')).toBeInTheDocument();
    expect(container.querySelector('.composer-actions')).toBeInTheDocument();
    expect(container.querySelector('.model-picker .composer-model')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Voice input unavailable' })).toBeDisabled();
    expect(screen.getByText('No branch').closest('.composer-chip')).toHaveAttribute(
      'data-disabled-reason',
      'GIT_BRANCH_CONTEXT_UNAVAILABLE',
    );
  });

  it('uses governance-accurate Turkish approval labels', async () => {
    const { user } = renderOperatorPanel(
      <ComposerHarness onSend={vi.fn()} variant="product" locale="tr" />,
    );

    expect(screen.getByText('Riske göre onay iste')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /profil varsayılanı/i }));
    await user.selectOptions(screen.getByLabelText('Approval profile'), 'policy_automatic');
    expect(screen.getByText('Politika içinde otomatik')).toBeInTheDocument();
  });

  it('selects provider/model metadata and sends it with the message', async () => {
    const onSend = vi.fn();
    const { user } = renderOperatorPanel(
      <ComposerHarness onSend={onSend} modelDiscovery={discoveredModels} />,
    );

    await user.selectOptions(screen.getByLabelText('Assistant provider'), 'ollama');
    await user.selectOptions(screen.getByLabelText('Assistant model'), 'qwen3.5:4b');
    await user.selectOptions(screen.getByLabelText('Assistant fallback provider'), 'transformers');
    await user.type(screen.getByLabelText('Message'), 'Summarize the active run.');

    expect(screen.getByLabelText('Selected assistant model')).toHaveTextContent('ollama / qwen3.5:4b');

    await user.click(screen.getByRole('button', { name: 'Send' }));

    expect(onSend).toHaveBeenCalledWith(
      'Summarize the active run.',
      expect.objectContaining({
        assistantProvider: 'ollama',
        assistantFallbackProvider: 'transformers',
        assistantModel: 'qwen3.5:4b',
        assistantHfModelId: '',
      }),
      expect.objectContaining({
        contextAttachmentKinds: expect.arrayContaining(['active_run', 'event_tail']),
        toolIntents: expect.arrayContaining(['inspect_run']),
      }),
    );
  });

  it('shows validation and blocks send for invalid provider/model combinations', async () => {
    const onSend = vi.fn();
    const { user } = renderOperatorPanel(<ComposerHarness onSend={onSend} />);

    await user.selectOptions(screen.getByLabelText('Assistant provider'), 'ollama');
    await user.type(screen.getByLabelText('Assistant model'), 'bad model');
    await user.type(screen.getByLabelText('Message'), 'Run with invalid metadata.');

    expect(screen.getByRole('alert')).toHaveTextContent('Model may only include');
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();

    await user.click(screen.getByRole('button', { name: 'Send' }));
    expect(onSend).not.toHaveBeenCalled();
  });

  it('sends with Enter and keeps Shift+Enter for multiline drafts', async () => {
    const onSend = vi.fn();
    const { user } = renderOperatorPanel(<ComposerHarness onSend={onSend} />);
    const messageBox = screen.getByLabelText('Message');

    await user.click(messageBox);
    await user.keyboard('First line');
    await user.keyboard('{Shift>}{Enter}{/Shift}');
    await user.keyboard('Second line');

    expect(onSend).not.toHaveBeenCalled();
    expect(messageBox).toHaveValue('First line\nSecond line');

    await user.keyboard('{Enter}');

    expect(onSend).toHaveBeenCalledWith(
      'First line\nSecond line',
      expect.any(Object),
      expect.any(Object),
    );
    expect(messageBox).toHaveValue('');
  });

  it('allows selecting safe tools and context attachments', async () => {
    const onSend = vi.fn();
    const { user } = renderOperatorPanel(<ComposerHarness onSend={onSend} />);

    await user.click(screen.getByLabelText('Attach context'));
    await user.click(screen.getByLabelText('Artifacts'));
    await user.click(screen.getByText('Tools'));
    await user.click(screen.getByLabelText('Draft plan'));
    await user.type(screen.getByLabelText('Message'), 'Prepare next steps.');
    await user.click(screen.getByRole('button', { name: 'Send' }));

    expect(onSend).toHaveBeenCalledWith(
      'Prepare next steps.',
      expect.any(Object),
      expect.objectContaining({
        contextAttachmentKinds: expect.not.arrayContaining(['artifact_summary']),
        toolIntents: expect.arrayContaining(['inspect_run', 'draft_remediation_plan']),
      }),
    );
  });

  it('maps a registered slash command to safe controls and rejects unknown commands', async () => {
    const onSend = vi.fn();
    const { user } = renderOperatorPanel(<ComposerHarness onSend={onSend} />);

    await user.type(screen.getByLabelText('Message'), '/inspect-run summarize the active deployment');
    await user.click(screen.getByRole('button', { name: 'Send' }));

    expect(onSend).toHaveBeenCalledWith(
      'summarize the active deployment',
      expect.any(Object),
      expect.objectContaining({
        contextAttachmentKinds: expect.arrayContaining(['active_run']),
        toolIntents: expect.arrayContaining(['inspect_run']),
      }),
    );

    await user.type(screen.getByLabelText('Message'), '/full-access deploy now');
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Send' })).toHaveAttribute(
      'data-disabled-reason',
      'This slash command is not available in the governed assistant.',
    );
  });

  it('keeps the stop action available while a turn is running', async () => {
    const onSend = vi.fn();
    const onCancel = vi.fn();
    const { user } = renderOperatorPanel(
      <AssistantComposer
        label="Message"
        placeholder="Ask about systems"
        sendLabel="Send"
        disabled
        runtimeSettings={DEFAULT_ASSISTANT_RUNTIME_SETTINGS}
        onRuntimeSettingsChange={vi.fn()}
        onSend={onSend}
        onCancel={onCancel}
      />,
    );

    const stopButton = screen.getByRole('button', { name: 'Stop' });

    expect(stopButton).toBeEnabled();

    await user.click(stopButton);

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onSend).not.toHaveBeenCalled();
  });
});
