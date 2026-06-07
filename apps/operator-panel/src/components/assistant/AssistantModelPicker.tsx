import type { AssistantProviderKind, AssistantProviderModelCandidate } from '../../assistant/modelDiscovery';
import type { AssistantModelDiscoveryState } from '../../assistant/useAssistantModels';
import { assistantUiText, translateAssistantText, type UiLocale } from '../../i18n';
import type { AssistantRuntimeSettings } from '../../settings';

type AssistantModelPickerProps = {
  runtimeSettings: AssistantRuntimeSettings;
  modelDiscovery?: AssistantModelDiscoveryState | null;
  locale?: UiLocale;
  onRuntimeSettingsChange: (next: Partial<AssistantRuntimeSettings>) => void;
};

const PROVIDER_VALUES = ['', 'auto', 'ollama', 'transformers'];
const FALLBACK_VALUES = ['', 'transformers', 'ollama'];

function providerFromSettings(settings: AssistantRuntimeSettings): AssistantProviderKind | 'default' {
  if (
    settings.assistantProvider === 'auto' ||
    settings.assistantProvider === 'ollama' ||
    settings.assistantProvider === 'transformers'
  ) {
    return settings.assistantProvider;
  }
  return 'default';
}

function modelsForProvider(
  models: AssistantProviderModelCandidate[],
  provider: AssistantProviderKind,
): AssistantProviderModelCandidate[] {
  return models.filter((model) => model.provider === provider);
}

function modelOptionLabel(model: AssistantProviderModelCandidate, locale: UiLocale): string {
  const suffix = model.installed ? '' : ` (${translateAssistantText('configured', locale)})`;
  return `${model.displayName || model.id}${suffix}`;
}

export function AssistantModelPicker({
  runtimeSettings,
  modelDiscovery,
  locale = 'en',
  onRuntimeSettingsChange,
}: AssistantModelPickerProps) {
  const text = assistantUiText[locale];
  const provider = providerFromSettings(runtimeSettings);
  const ollamaModels = modelsForProvider(modelDiscovery?.models ?? [], 'ollama');
  const transformerModels = modelsForProvider(modelDiscovery?.models ?? [], 'transformers');
  const discoveryStatus = modelDiscovery?.status ?? 'idle';
  const isDiscovering = discoveryStatus === 'loading';
  const discoveryError = modelDiscovery?.error;

  const updateRuntimeSetting = (key: keyof AssistantRuntimeSettings, value: string) => {
    onRuntimeSettingsChange({ [key]: value });
  };

  const updateProvider = (value: string) => {
    if (value === 'ollama') {
      onRuntimeSettingsChange({ assistantProvider: value, assistantHfModelId: '' });
      return;
    }
    if (value === 'transformers') {
      onRuntimeSettingsChange({ assistantProvider: value, assistantModel: '' });
      return;
    }
    onRuntimeSettingsChange({ assistantProvider: value });
  };
  const onRefreshModels = () => {
    modelDiscovery?.refresh();
  };

  const discoveryHelper =
    discoveryError?.message ||
    (discoveryStatus === 'empty'
      ? translateAssistantText('No local assistant models were discovered. Use refresh after installing a model.', locale)
      : isDiscovering
        ? translateAssistantText('Discovering local assistant models...', locale)
        : '');
  const refreshTitle = isDiscovering
    ? translateAssistantText('Assistant model discovery is already running.', locale)
    : translateAssistantText('Refresh assistant models', locale);
  const optionLabel = (value: string) => (value ? value : text.useProfileDefault);

  return (
    <div className="assistant-runtime-settings" aria-label="Assistant runtime settings">
      <label>
        <span>{text.provider}</span>
        <select
          aria-label="Assistant provider"
          value={runtimeSettings.assistantProvider}
          onChange={(event) => updateProvider(event.target.value)}
        >
          {PROVIDER_VALUES.map((value) => (
            <option key={value || 'default'} value={value}>
              {optionLabel(value)}
            </option>
          ))}
        </select>
      </label>

      {provider === 'ollama' ? (
        <label>
          <span>{text.model}</span>
          {ollamaModels.length > 0 ? (
            <select
              aria-label="Assistant model"
              value={runtimeSettings.assistantModel}
              onChange={(event) => updateRuntimeSetting('assistantModel', event.target.value)}
            >
              <option value="">{text.useProfileDefault}</option>
              {ollamaModels.map((model) => (
                <option key={`${model.provider}:${model.id}`} value={model.id}>
                  {modelOptionLabel(model, locale)}
                </option>
              ))}
            </select>
          ) : (
            <input
              aria-label="Assistant model"
              value={runtimeSettings.assistantModel}
              onChange={(event) => updateRuntimeSetting('assistantModel', event.target.value)}
              placeholder="qwen3.5:4b"
            />
          )}
        </label>
      ) : null}

      {provider === 'transformers' ? (
        <label>
          <span>{text.hfModelId}</span>
          {transformerModels.length > 0 ? (
            <select
              aria-label="Assistant HF model id"
              value={runtimeSettings.assistantHfModelId}
              onChange={(event) => updateRuntimeSetting('assistantHfModelId', event.target.value)}
            >
              <option value="">{text.useProfileDefault}</option>
              {transformerModels.map((model) => (
                <option key={`${model.provider}:${model.id}`} value={model.id}>
                  {modelOptionLabel(model, locale)}
                </option>
              ))}
            </select>
          ) : (
            <input
              aria-label="Assistant HF model id"
              value={runtimeSettings.assistantHfModelId}
              onChange={(event) => updateRuntimeSetting('assistantHfModelId', event.target.value)}
              placeholder="Qwen/Qwen2.5"
            />
          )}
        </label>
      ) : null}

      {provider === 'default' || provider === 'auto' ? (
        <label>
          <span>{text.model}</span>
          <input aria-label="Assistant model" value={text.profileManaged} readOnly />
        </label>
      ) : null}

      <label>
        <span>{text.fallback}</span>
        <select
          aria-label="Assistant fallback provider"
          value={runtimeSettings.assistantFallbackProvider}
          onChange={(event) => updateRuntimeSetting('assistantFallbackProvider', event.target.value)}
        >
          {FALLBACK_VALUES.map((value) => (
            <option key={value || 'default'} value={value}>
              {optionLabel(value)}
            </option>
          ))}
        </select>
      </label>

      <div className="assistant-model-discovery-status" aria-live="polite">
        {discoveryHelper ? <span>{discoveryHelper}</span> : <span>{`${modelDiscovery?.models.length ?? 0} ${text.modelsFound}`}</span>}
        {modelDiscovery ? (
          <button
            type="button"
            onClick={onRefreshModels}
            disabled={isDiscovering}
            title={refreshTitle}
            data-disabled-reason={isDiscovering ? refreshTitle : undefined}
          >
            {text.refresh}
          </button>
        ) : null}
      </div>
    </div>
  );
}
