import type { PlatformEvidenceViewModel, RcHandoffViewModel } from './platformEvidenceTypes';

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function readString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function readStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

export function mapPlatformEvidenceReconciliation(payload: unknown): PlatformEvidenceViewModel {
  const root = asRecord(payload);
  const targetsRecord = asRecord(root.targets);
  const targets = Object.entries(targetsRecord).map(([targetId, value]) => {
    const target = asRecord(value);
    return {
      targetId,
      status: readString(target.status, 'not_evidenced'),
      reasonCodes: readStringArray(target.reasonCodes),
    };
  });
  const blockers = Array.isArray(root.noShipBlockers)
    ? root.noShipBlockers.map((item) => readString(asRecord(item).reasonCode)).filter(Boolean)
    : [];
  return {
    status: readString(root.status, 'pass'),
    evidencedTargets: readStringArray(root.evidencedTargets),
    notEvidencedTargets: readStringArray(root.notEvidencedTargets),
    blockers,
    targets,
  };
}

export function mapRcHandoff(payload: unknown): RcHandoffViewModel {
  const root = asRecord(payload);
  return {
    status: readString(root.status, 'conditional'),
    branch: readString(root.branch, 'unknown'),
    gitCommit: readString(root.gitCommit, 'unknown'),
    supportedClaims: readStringArray(root.supportedClaims),
    blockedClaims: readStringArray(root.blockedClaims),
    nextSteps: readStringArray(root.operatorNextSteps),
  };
}
