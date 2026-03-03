import { describe, expect, it } from 'vitest';

import { actorForOperator, canMutateWithOperatorId } from './operator';

describe('mutation guard', () => {
  it('disables mutations when operator id is invalid', () => {
    expect(canMutateWithOperatorId('', false)).toBe(false);
    expect(canMutateWithOperatorId('ab', false)).toBe(false);
    expect(canMutateWithOperatorId('bad value', false)).toBe(false);
  });

  it('disables mutations when contract is mismatched', () => {
    expect(canMutateWithOperatorId('ops-team_01', true)).toBe(false);
  });

  it('enables mutations for valid operator id and matching contract', () => {
    expect(canMutateWithOperatorId('ops-team_01', false)).toBe(true);
  });
});

describe('operator actor format', () => {
  it('uses ui namespace', () => {
    expect(actorForOperator(' ops-team_01 ')).toBe('ui:ops-team_01');
  });
});
