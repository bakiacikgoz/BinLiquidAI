export type CoreMode = 'auto' | 'external' | 'bundled';
export type LocaleMode = 'auto' | 'en' | 'tr';
export type UpdaterMode = 'off' | 'manual' | 'auto';

export interface PanelSettings {
  mode: CoreMode;
  cliPath: string;
  bundledPythonPath: string;
  profile: string;
  rootDir: string;
  operatorId: string;
  locale: LocaleMode;
  remoteTelemetry: boolean;
  updaterMode: UpdaterMode;
  debugRaw: boolean;
}

export const SETTINGS_KEY = 'aegisos.operator.settings.v1';

export const DEFAULT_SETTINGS: PanelSettings = {
  mode: 'auto',
  cliPath: '',
  bundledPythonPath: '',
  profile: 'balanced',
  rootDir: '.binliquid/team/jobs',
  operatorId: '',
  locale: 'auto',
  remoteTelemetry: false,
  updaterMode: 'off',
  debugRaw: false,
};

export function loadSettings(): PanelSettings {
  const raw = globalThis.localStorage?.getItem(SETTINGS_KEY);
  if (!raw) {
    return { ...DEFAULT_SETTINGS };
  }

  try {
    const parsed = JSON.parse(raw) as Partial<PanelSettings>;
    return {
      ...DEFAULT_SETTINGS,
      ...parsed,
    };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

export function saveSettings(settings: PanelSettings): void {
  globalThis.localStorage?.setItem(SETTINGS_KEY, JSON.stringify(settings));
}

export function resolveLocale(locale: LocaleMode): 'en' | 'tr' {
  if (locale === 'en' || locale === 'tr') {
    return locale;
  }
  const browserLocale = (globalThis.navigator?.language ?? 'en').toLowerCase();
  return browserLocale.startsWith('tr') ? 'tr' : 'en';
}

export const OPERATOR_ID_PATTERN = /^[a-zA-Z0-9._-]{3,64}$/;

export function isOperatorIdValid(value: string): boolean {
  return OPERATOR_ID_PATTERN.test(value.trim());
}
