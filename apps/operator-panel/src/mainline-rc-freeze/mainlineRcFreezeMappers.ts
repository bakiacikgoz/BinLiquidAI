import type { MainlineRcFreezeBadge, MainlineRcFreezeSnapshot } from './mainlineRcFreezeTypes';

export function mapMainlineRcFreeze(
  snapshot?: MainlineRcFreezeSnapshot | null,
): MainlineRcFreezeSnapshot {
  return (
    snapshot ?? {
      schemaVersion: 'control-plane.mainline-rc-freeze-snapshot/v1',
      status: 'missing',
      freezeId: null,
      manifestPath: null,
      stackStatus: 'missing',
      mergeRehearsalStatus: 'missing',
      gateEvidenceStatus: 'missing',
      artifactScanStatus: 'missing',
      evidenceMode: 'hash_only',
      rawPersistence: false,
      blockers: [],
      warnings: ['MAINLINE_RC_FREEZE_MISSING'],
      lastGeneratedAtUtc: null,
    }
  );
}

export function mainlineRcFreezeBadges(
  snapshot: MainlineRcFreezeSnapshot,
): MainlineRcFreezeBadge[] {
  return [
    { label: snapshot.status, tone: toneFor(snapshot.status) },
    { label: `stack_${snapshot.stackStatus}`, tone: toneFor(snapshot.stackStatus) },
    { label: `merge_${snapshot.mergeRehearsalStatus}`, tone: toneFor(snapshot.mergeRehearsalStatus) },
    { label: `gates_${snapshot.gateEvidenceStatus}`, tone: toneFor(snapshot.gateEvidenceStatus) },
    { label: `scan_${snapshot.artifactScanStatus}`, tone: toneFor(snapshot.artifactScanStatus) },
  ];
}

function toneFor(value?: string): MainlineRcFreezeBadge['tone'] {
  if (value === 'ready' || value === 'pass') return 'ready';
  if (value === 'blocked' || value === 'fail' || value === 'failed') return 'blocked';
  if (value === 'missing' || value === 'conditional') return 'warning';
  return 'neutral';
}
