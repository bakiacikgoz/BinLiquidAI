export type PlatformTargetViewModel = {
  os: string;
  arch: string;
  targetId: string;
  supportTier: 'supported' | 'experimental' | 'not_evidenced' | 'unsupported' | string;
  claimAllowed: boolean;
  reasonCodes: string[];
};

export type LocalProductReadinessViewModel = {
  schemaVersion: string;
  overallStatus: string;
  currentTarget: PlatformTargetViewModel;
  supportedClaims: string[];
  notEvidencedTargets: string[];
  unsupportedTargets: string[];
  blockedTargets: string[];
  productClaimSummary: string;
  blockingReasons: string[];
};

