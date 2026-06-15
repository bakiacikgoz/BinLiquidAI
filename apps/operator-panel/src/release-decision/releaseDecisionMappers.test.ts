import { describe, expect, it } from 'vitest';

import { mapReleaseDecision, releaseDecisionBadges } from './releaseDecisionMappers';

describe('release decision mappers', () => {
  it('maps missing dossier to not_available without claiming readiness', () => {
    const snapshot = mapReleaseDecision(null);

    expect(snapshot.status).toBe('not_available');
    expect(snapshot.signoffStatus).toBe('missing');
    expect(releaseDecisionBadges(snapshot).some((badge) => badge.label.includes('approved'))).toBe(false);
  });
});
