export type HarvestTargetResult = {
  target: string;
  status: string;
  reasonCodes: string[];
};

export type PlatformEvidenceHarvestViewModel = {
  status: string;
  headSha: string;
  artifactsDiscovered: number;
  artifactsImported: number;
  warnings: string[];
  blockers: string[];
  targets: HarvestTargetResult[];
};

export type SourceInstallRcClaimViewModel = {
  status: string;
  claimSet: string;
  claimedTargets: string[];
  notEvidencedTargets: string[];
  blockedTargets: Array<{ target: string; reasonCode: string }>;
  allowedClaims: string[];
};

export type TargetClosureActionViewModel = {
  target: string;
  status: string;
  recommendedPath: string;
  commands: string[];
  runbook: string;
  reasonCodes: string[];
};

