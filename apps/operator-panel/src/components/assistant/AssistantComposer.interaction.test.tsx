import { useState } from 'react';
import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import {
  DEFAULT_ASSISTANT_RUNTIME_SETTINGS,
  type AssistantRuntimeSettings,
} from '../../settings';
import { renderOperatorPanel } from '../../test/render';
import { AssistantComposer } from './AssistantComposer';

function ComposerHarness({
  onSend,
}: {
  onSend: (message: string, runtimeSettings: AssistantRuntimeSettings) => void;
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
      onRuntimeSettingsChange={(next) => setRuntimeSettings((prev) => ({ ...prev, ...next }))}
      onSend={onSend}
    />
  );
}

describe('AssistantComposer runtime controls', () => {
  it('selects provider/model metadata and sends it with the message', async () => {
    const onSend = vi.fn();
    const { user } = renderOperatorPanel(<ComposerHarness onSend={onSend} />);

    await user.selectOptions(screen.getByLabelText('Assistant provider'), 'ollama');
    await user.type(screen.getByLabelText('Assistant model'), 'qwen3.5:4b');
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
    );
  });

  it('shows validation and blocks send for invalid provider/model combinations', async () => {
    const onSend = vi.fn();
    const { user } = renderOperatorPanel(<ComposerHarness onSend={onSend} />);

    await user.selectOptions(screen.getByLabelText('Assistant provider'), 'transformers');
    await user.type(screen.getByLabelText('Assistant model'), 'qwen3.5:4b');
    await user.type(screen.getByLabelText('Message'), 'Run with invalid metadata.');

    expect(screen.getByRole('alert')).toHaveTextContent('Use HF model id');
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();

    await user.click(screen.getByRole('button', { name: 'Send' }));
    expect(onSend).not.toHaveBeenCalled();
  });
});
