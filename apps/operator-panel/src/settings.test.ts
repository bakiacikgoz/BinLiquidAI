import { beforeEach, describe, expect, it } from 'vitest';

import {
  DEFAULT_OPERATOR_ID,
  DEFAULT_SETTINGS,
  SETTINGS_KEY,
  assistantRuntimeOptionsFromSettings,
  isOperatorIdValid,
  loadSettings,
  resolveLocale,
  validateAssistantRuntimeSettings,
} from './settings';

beforeEach(() => {
  localStorage.clear();
});

describe('operator id validation', () => {
  it('accepts expected format', () => {
    expect(isOperatorIdValid('ops-team_01')).toBe(true);
  });

  it('rejects invalid format', () => {
    expect(isOperatorIdValid('ab')).toBe(false);
    expect(isOperatorIdValid('bad value')).toBe(false);
    expect(isOperatorIdValid('bad*id')).toBe(false);
  });

  it('ships with a valid local operator id for first-run use', () => {
    expect(DEFAULT_SETTINGS.operatorId).toBe(DEFAULT_OPERATOR_ID);
    expect(isOperatorIdValid(DEFAULT_SETTINGS.operatorId)).toBe(true);
  });

  it('migrates missing or blank legacy operator id settings to the local default', () => {
    localStorage.setItem(
      SETTINGS_KEY,
      JSON.stringify({
        mode: 'auto',
        profile: 'balanced',
        rootDir: '.binliquid/team/jobs',
        operatorId: '',
      }),
    );

    expect(loadSettings().operatorId).toBe(DEFAULT_OPERATOR_ID);

    localStorage.setItem(
      SETTINGS_KEY,
      JSON.stringify({
        mode: 'auto',
        profile: 'balanced',
        rootDir: '.binliquid/team/jobs',
      }),
    );

    expect(loadSettings().operatorId).toBe(DEFAULT_OPERATOR_ID);
  });

  it('preserves invalid explicit operator ids so the mutation gate can fail closed', () => {
    localStorage.setItem(
      SETTINGS_KEY,
      JSON.stringify({
        ...DEFAULT_SETTINGS,
        operatorId: 'ab',
      }),
    );

    expect(loadSettings().operatorId).toBe('ab');
    expect(isOperatorIdValid(loadSettings().operatorId)).toBe(false);
  });
});

describe('locale resolver', () => {
  it('respects explicit locale', () => {
    expect(resolveLocale('en')).toBe('en');
    expect(resolveLocale('tr')).toBe('tr');
  });
});

describe('assistant runtime settings', () => {
  it('loads legacy settings with profile-default assistant runtime fields', () => {
    localStorage.setItem(
      SETTINGS_KEY,
      JSON.stringify({
        mode: 'auto',
        profile: 'balanced',
        rootDir: '.binliquid/team/jobs',
      }),
    );

    expect(loadSettings()).toEqual(
      expect.objectContaining({
        assistantProvider: '',
        assistantFallbackProvider: '',
        assistantModel: '',
        assistantHfModelId: '',
        assistantOpenAiApiKey: '',
        assistantDeepSeekApiKey: '',
      }),
    );
  });

  it('preserves assistant API keys from stored settings', () => {
    localStorage.setItem(
      SETTINGS_KEY,
      JSON.stringify({
        ...DEFAULT_SETTINGS,
        assistantOpenAiApiKey: 'sk-openai',
        assistantDeepSeekApiKey: 'sk-deepseek',
      }),
    );

    expect(loadSettings()).toEqual(
      expect.objectContaining({
        assistantOpenAiApiKey: 'sk-openai',
        assistantDeepSeekApiKey: 'sk-deepseek',
      }),
    );
  });

  it('leaves empty assistant runtime overrides undefined for CLI defaults', () => {
    expect(assistantRuntimeOptionsFromSettings({ ...DEFAULT_SETTINGS })).toEqual({
      provider: undefined,
      providerId: undefined,
      fallbackProvider: undefined,
      fallbackProviderId: undefined,
      model: undefined,
      hfModelId: undefined,
    });
  });

  it('maps canonical provider ids separately from legacy provider flags', () => {
    expect(
      assistantRuntimeOptionsFromSettings({
        ...DEFAULT_SETTINGS,
        assistantProvider: 'company-internal',
        assistantFallbackProvider: 'local-transformers',
      }),
    ).toEqual(
      expect.objectContaining({
        provider: undefined,
        providerId: 'company-internal',
        fallbackProvider: undefined,
        fallbackProviderId: 'local-transformers',
      }),
    );
  });

  it('validates provider-specific model override combinations', () => {
    expect(
      validateAssistantRuntimeSettings({
        assistantProvider: 'ollama',
        assistantFallbackProvider: 'transformers',
        assistantModel: 'qwen3.5:4b',
        assistantHfModelId: '',
      }),
    ).toBe('');

    expect(
      validateAssistantRuntimeSettings({
        assistantProvider: 'transformers',
        assistantFallbackProvider: '',
        assistantModel: 'qwen3.5:4b',
        assistantHfModelId: '',
      }),
    ).toContain('Use HF model id');
  });
});
