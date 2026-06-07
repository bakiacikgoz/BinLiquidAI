export type AssistantProviderKind = 'auto' | 'ollama' | 'transformers';

export type AssistantProviderModelSource = 'ollama' | 'transformers_cache' | 'config' | 'preview_fixture';

export type AssistantProviderModelsRequest = {
  profile: string;
  provider?: AssistantProviderKind | 'all';
  refresh?: boolean;
};

export type AssistantProviderModelCandidate = {
  provider: AssistantProviderKind;
  id: string;
  displayName: string;
  installed: boolean;
  configured: boolean;
  source: AssistantProviderModelSource;
  family?: string;
  sizeBytes?: number | null;
  modifiedAtUtc?: string | null;
  warnings: string[];
};

export type AssistantProviderModelsProvider = {
  provider: AssistantProviderKind;
  available: boolean;
  selectedByConfig: boolean;
  errorCode?: string;
  errorMessage?: string;
  models: AssistantProviderModelCandidate[];
};

export type AssistantProviderModelsResponse = {
  contractVersion: 'operator-panel.assistant-provider-models/v1';
  profile: string;
  provider: AssistantProviderKind | 'all';
  generatedAtUtc: string;
  providers: AssistantProviderModelsProvider[];
};

export function flattenAssistantModels(
  response: AssistantProviderModelsResponse,
  provider: AssistantProviderKind | 'all' = 'all',
): AssistantProviderModelCandidate[] {
  return response.providers
    .filter((item) => provider === 'all' || item.provider === provider)
    .flatMap((item) => item.models);
}

