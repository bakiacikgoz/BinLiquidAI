export interface RcGateEvidenceSnapshot {
  schemaVersion: 'control-plane.rc-gate-evidence-snapshot/v1';
  status: 'ready' | 'conditional' | 'blocked' | 'missing';
  target: string;
  latestLedgerRef?: string | null;
  latestVerificationRef?: string | null;
  verifiedGateCount: number;
  missingGateCount: number;
  missingArtifactCount: number;
  secretScanStatus: string;
  rawMarkerScanStatus: string;
  platform: string;
  makeRequired: boolean;
  readyForRcFreeze: boolean;
  blockingReasons: string[];
  warnings: string[];
}
