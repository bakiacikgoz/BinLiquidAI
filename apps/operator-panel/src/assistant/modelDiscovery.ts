export type AssistantProviderKind =
  | 'auto'
  | 'ollama'
  | 'transformers'
  | 'local_ollama'
  | 'local_transformers'
  | 'openai_compatible'
  | 'openai_responses'
  | 'company_internal_api'
  | 'openai'
  | 'azure_openai'
  | 'anthropic'
  | 'google_gemini'
  | 'deepseek'
  | 'openrouter'
  | 'custom_http';

export type AssistantProviderId = string;

export type AssistantProviderModelSource =
  | 'ollama'
  | 'transformers_cache'
  | 'config'
  | 'preview_fixture';

export type AssistantProviderModelsRequest = {
  profile: string;
  provider?: AssistantProviderId | 'all';
  refresh?: boolean;
};

export type AssistantProviderModelCandidate = {
  provider: AssistantProviderId;
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
  provider: AssistantProviderId;
  legacyProvider?: 'ollama' | 'transformers' | null;
  kind?: AssistantProviderKind;
  displayName?: string;
  dataBoundary?: string | null;
  riskTier?: string | null;
  trustSource?: 'preview_fixture' | 'live_evidence' | 'bridge_state' | string | null;
  lastCanaryStatus?: string | null;
  lastCanaryReason?: string | null;
  lastCanaryAtUtc?: string | null;
  lastVerifiedEvidenceAtUtc?: string | null;
  evidencePath?: string | null;
  budgetState?: string | null;
  budgetReason?: string | null;
  conformanceStatus?: string | null;
  conformanceReason?: string | null;
  conformanceSummary?: string | null;
  nativeAdapterKind?: string | null;
  nativeAdapterStatus?: string | null;
  storagePolicy?: string | null;
  serverToolsPolicy?: string | null;
  customToolsPolicy?: string | null;
  available: boolean;
  selectedByConfig: boolean;
  disabledReason?: string | null;
  errorCode?: string;
  errorMessage?: string;
  models: AssistantProviderModelCandidate[];
};

export type AssistantProviderModelsResponse = {
  contractVersion:
    | 'operator-panel.assistant-provider-models/v1'
    | 'operator-panel.assistant-provider-models/v2'
    | 'operator-panel.assistant-provider-models/v3';
  profile: string;
  provider: AssistantProviderId | 'all';
  generatedAtUtc: string;
  providers: AssistantProviderModelsProvider[];
};

export function flattenAssistantModels(
  response: AssistantProviderModelsResponse,
  provider: AssistantProviderId | 'all' = 'all',
): AssistantProviderModelCandidate[] {
  return response.providers
    .filter((item) => provider === 'all' || item.provider === provider)
    .flatMap((item) => item.models);
}

