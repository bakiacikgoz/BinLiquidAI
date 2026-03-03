import { describe, expect, it } from 'vitest';

import { isOperatorIdValid, resolveLocale } from './settings';

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
