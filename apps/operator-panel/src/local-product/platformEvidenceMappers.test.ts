import { describe, expect, it } from 'vitest';

import { mapPlatformEvidenceReconciliation, mapRcHandoff } from './platformEvidenceMappers';

describe('platformEvidenceMappers', () => {
  it('maps platform evidence reconciliation target statuses', () => {
    const vm = mapPlatformEvidenceReconciliation({
      status: 'pass',
      evidencedTargets: ['windows-x64'],
      notEvidencedTargets: ['darwin-arm64'],
      noShipBlockers: [],
      targets: {
        'windows-x64': { status: 'evidenced', reasonCodes: [] },
        'darwin-arm64': { status: 'not_evidenced', reasonCodes: ['TARGET_NOT_EVIDENCED'] },
      },
    });

    expect(vm.evidencedTargets).toEqual(['windows-x64']);
    expect(vm.targets[1]?.status).toBe('not_evidenced');
  });

  it('maps rc handoff manifests', () => {
    const vm = mapRcHandoff({
      status: 'ready',
      branch: 'codex/example',
      gitCommit: 'abc123',
      supportedClaims: ['windows-x64 source/local install evidenced'],
      blockedClaims: [],
      operatorNextSteps: ['Collect missing target evidence.'],
    });

    expect(vm.status).toBe('ready');
    expect(vm.supportedClaims).toHaveLength(1);
  });
});
