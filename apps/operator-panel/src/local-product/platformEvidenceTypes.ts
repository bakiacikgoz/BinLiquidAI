export type PlatformEvidenceTargetViewModel = {
  targetId: string;
  status: string;
  reasonCodes: string[];
};

export type PlatformEvidenceViewModel = {
  status: string;
  evidencedTargets: string[];
  notEvidencedTargets: string[];
  blockers: string[];
  targets: PlatformEvidenceTargetViewModel[];
};

export type RcHandoffViewModel = {
  status: string;
  branch: string;
  gitCommit: string;
  supportedClaims: string[];
  blockedClaims: string[];
  nextSteps: string[];
};
