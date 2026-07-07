import { describe, expect, it } from 'vitest';

import {
  mapPlatformEvidenceHarvest,
  mapSourceInstallRcClaim,
  mapTargetClosureActions,
} from './platformEvidenceHarvestMappers';

describe('platform evidence harvest mappers', () => {
  it('maps harvest, source claim, and target actions defensively', () => {
    expect(
      mapPlatformEvidenceHarvest({
        status: 'pass',
        headSha: 'abc',
        artifactsDiscovered: 1,
        artifactsImported: 1,
        targetResults: [{ target: 'windows-x64', status: 'evidenced', reasonCodes: [] }],
      }).targets[0].target,
    ).toBe('windows-x64');

    expect(
      mapSourceInstallRcClaim({
        status: 'pass',
        claimedTargets: ['windows-x64'],
        releaseNotesAllowedClaims: ['windows-x64 source-local-install evidenced'],
      }).claimedTargets,
    ).toEqual(['windows-x64']);

    expect(
      mapTargetClosureActions([{ target: 'linux-x64', commands: ['uv run ...'] }])[0].target,
    ).toBe('linux-x64');
  });
});

