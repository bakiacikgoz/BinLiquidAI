import type { DesignPartnerHandoffSnapshot, HandoffBadge } from './designPartnerHandoffTypes';

export function mapDesignPartnerHandoff(
  snapshot?: DesignPartnerHandoffSnapshot | null,
): DesignPartnerHandoffSnapshot {
  return (
    snapshot ?? {
      schemaVersion: 'control-plane.design-partner-handoff-snapshot/v1',
      status: 'missing',
      handoffPackPath: null,
      releaseTrainStatus: 'missing',
      firstRunDrillStatus: 'missing',
      blockers: [],
      warnings: ['DESIGN_PARTNER_HANDOFF_MISSING'],
      lastGeneratedAtUtc: null,
      claimBoundarySummary: {
        publicDesktop: 'blocked',
        liveComputerUse: 'blocked',
        approvalFreeIrreversibleMutation: 'blocked',
      },
    }
  );
}

export function handoffBadges(snapshot: DesignPartnerHandoffSnapshot): HandoffBadge[] {
  return [
    { label: snapshot.status, tone: toneFor(snapshot.status) },
    { label: `release_train_${snapshot.releaseTrainStatus}`, tone: toneFor(snapshot.releaseTrainStatus) },
    { label: `first_run_${snapshot.firstRunDrillStatus}`, tone: toneFor(snapshot.firstRunDrillStatus) },
    { label: `public_desktop_${snapshot.claimBoundarySummary.publicDesktop ?? 'unknown'}`, tone: toneFor(snapshot.claimBoundarySummary.publicDesktop) },
    { label: `live_computer_use_${snapshot.claimBoundarySummary.liveComputerUse ?? 'unknown'}`, tone: toneFor(snapshot.claimBoundarySummary.liveComputerUse) },
  ];
}

function toneFor(value?: string): HandoffBadge['tone'] {
  if (value === 'ready' || value === 'pass' || value === 'blocked') {
    return value === 'blocked' ? 'blocked' : 'ready';
  }
  if (value === 'missing' || value === 'conditional') {
    return 'warning';
  }
  return 'neutral';
}
