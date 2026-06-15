import type { RcReleaseDecisionSnapshot, ReleaseDecisionBadge } from './releaseDecisionTypes';

export function mapReleaseDecision(
  snapshot?: RcReleaseDecisionSnapshot | null,
): RcReleaseDecisionSnapshot {
  return (
    snapshot ?? {
      schemaVersion: 'control-plane.rc-release-decision-snapshot/v1',
      status: 'not_available',
      signoffStatus: 'missing',
      hatAStatus: 'not_evaluated',
      hatBStatus: 'not_in_scope',
      designPartnerRcStatus: 'conditional',
      noShipBlockingCount: 0,
      externalBlockerCount: 0,
      evidenceRefCount: 0,
      blockingReasons: [],
      warnings: ['RC_RELEASE_DECISION_MISSING'],
    }
  );
}

export function releaseDecisionBadges(snapshot: RcReleaseDecisionSnapshot): ReleaseDecisionBadge[] {
  return [
    { label: snapshot.status, tone: toneFor(snapshot.status) },
    { label: `signoff:${snapshot.signoffStatus}`, tone: toneFor(snapshot.signoffStatus) },
    { label: `Hat A:${snapshot.hatAStatus}`, tone: toneFor(snapshot.hatAStatus) },
    { label: `Hat B:${snapshot.hatBStatus}`, tone: toneFor(snapshot.hatBStatus) },
  ];
}

function toneFor(value: string): ReleaseDecisionBadge['tone'] {
  if (value.includes('approved') || value === 'verified') return 'good';
  if (value.includes('blocked') || value === 'missing') return 'danger';
  if (value.includes('conditional') || value.includes('external')) return 'warn';
  return 'muted';
}
