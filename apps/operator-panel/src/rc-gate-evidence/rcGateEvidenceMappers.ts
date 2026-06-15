import type { RcGateEvidenceSnapshot } from './rcGateEvidenceTypes';

export function mapRcGateEvidence(snapshot?: RcGateEvidenceSnapshot | null): RcGateEvidenceSnapshot {
  if (!snapshot) {
    return {
      schemaVersion: 'control-plane.rc-gate-evidence-snapshot/v1',
      status: 'missing',
      target: 'mainline-rc',
      latestLedgerRef: null,
      latestVerificationRef: null,
      verifiedGateCount: 0,
      missingGateCount: 0,
      missingArtifactCount: 0,
      secretScanStatus: 'missing',
      rawMarkerScanStatus: 'missing',
      platform: 'unknown',
      makeRequired: false,
      readyForRcFreeze: false,
      blockingReasons: [],
      warnings: ['RC_GATE_EVIDENCE_LEDGER_MISSING'],
    };
  }
  return {
    ...snapshot,
    blockingReasons: snapshot.blockingReasons ?? [],
    warnings: snapshot.warnings ?? [],
  };
}

export function rcGateEvidenceBadges(snapshot: RcGateEvidenceSnapshot) {
  return [
    { label: `target_${snapshot.target}`, tone: 'neutral' },
    { label: `platform_${snapshot.platform}`, tone: 'neutral' },
    { label: `secret_${snapshot.secretScanStatus}`, tone: snapshot.secretScanStatus === 'pass' ? 'success' : 'warning' },
    { label: `raw_${snapshot.rawMarkerScanStatus}`, tone: snapshot.rawMarkerScanStatus === 'pass' ? 'success' : 'warning' },
  ];
}
