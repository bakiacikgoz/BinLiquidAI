import { beforeEach, describe, expect, it } from 'vitest';

import {
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
      }),
    );
  });

  it('leaves empty assistant runtime overrides undefined for CLI defaults', () => {
    expect(assistantRuntimeOptionsFromSettings({ ...DEFAULT_SETTINGS })).toEqual({
      provider: undefined,
      fallbackProvider: undefined,
      model: undefined,
      hfModelId: undefined,
    });
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
