export type ArtifactFeatureFlagState = {
  workspace: boolean;
  document: boolean;
  form: boolean;
  code: boolean;
  flow: boolean;
  spreadsheet: boolean;
  canvas: boolean;
  slides: boolean;
  export: boolean;
  assistantUiRuntime: boolean;
  aiSdkTauriTransport: boolean;
};

type ArtifactFeatureFlagEnvironment = Record<string, string | boolean | undefined>;

type ArtifactEditorCapabilities = {
  spreadsheet?: boolean;
  canvas?: boolean;
};

const ALL_OFF: ArtifactFeatureFlagState = {
  workspace: false,
  document: false,
  form: false,
  code: false,
  flow: false,
  spreadsheet: false,
  canvas: false,
  slides: false,
  export: false,
  assistantUiRuntime: false,
  aiSdkTauriTransport: false,
};

function enabled(value: string | boolean | undefined): boolean {
  return value === true || value === '1' || value?.toString().toLowerCase() === 'true';
}

export function resolveArtifactFeatureFlags(
  environment: ArtifactFeatureFlagEnvironment,
  capabilities: ArtifactEditorCapabilities = {},
): ArtifactFeatureFlagState {
  if (!enabled(environment.VITE_ARTIFACT_WORKSPACE)) return { ...ALL_OFF };
  return {
    workspace: true,
    document: enabled(environment.VITE_ARTIFACT_DOCUMENT_EDITOR),
    form: enabled(environment.VITE_ARTIFACT_FORM_EDITOR),
    code: enabled(environment.VITE_ARTIFACT_CODE_EDITOR),
    flow: enabled(environment.VITE_ARTIFACT_FLOW_EDITOR),
    spreadsheet: enabled(environment.VITE_ARTIFACT_SPREADSHEET_EDITOR) && capabilities.spreadsheet === true,
    canvas: enabled(environment.VITE_ARTIFACT_CANVAS_EDITOR) && capabilities.canvas === true,
    slides: enabled(environment.VITE_ARTIFACT_SLIDES_EDITOR),
    export: enabled(environment.VITE_ARTIFACT_EXPORT),
    assistantUiRuntime: enabled(environment.VITE_ASSISTANT_UI_RUNTIME),
    aiSdkTauriTransport: enabled(environment.VITE_ASSISTANT_AI_SDK_RUNTIME),
  };
}

export function isArtifactFormEditorEnabled(value: string | undefined): boolean {
  return enabled(value);
}

export function isArtifactCodeEditorEnabled(value: string | undefined): boolean {
  return enabled(value);
}

export function isArtifactFlowEditorEnabled(value: string | undefined): boolean {
  return enabled(value);
}

export function isArtifactSlidesEditorEnabled(value: string | undefined): boolean {
  return enabled(value);
}
