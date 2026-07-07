import type {
  PlatformEvidenceHarvestViewModel,
  SourceInstallRcClaimViewModel,
  TargetClosureActionViewModel,
} from './platformEvidenceHarvestTypes';

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function readString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function readNumber(value: unknown): number {
  return typeof value === 'number' ? value : 0;
}

function readStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

export function mapPlatformEvidenceHarvest(payload: unknown): PlatformEvidenceHarvestViewModel {
  const root = asRecord(payload);
  const targets = Array.isArray(root.targetResults)
    ? root.targetResults.map((item) => {
        const target = asRecord(item);
        return {
          target: readString(target.target, 'unknown'),
          status: readString(target.status, 'not_evidenced'),
          reasonCodes: readStringArray(target.reasonCodes),
        };
      })
    : [];
  return {
    status: readString(root.status, 'conditional'),
    headSha: readString(root.headSha, 'unknown'),
    artifactsDiscovered: readNumber(root.artifactsDiscovered),
    artifactsImported: readNumber(root.artifactsImported),
    warnings: readStringArray(root.warnings),
    blockers: readStringArray(root.blockers),
    targets,
  };
}

export function mapSourceInstallRcClaim(payload: unknown): SourceInstallRcClaimViewModel {
  const root = asRecord(payload);
  const blockedTargets = Array.isArray(root.blockedTargets)
    ? root.blockedTargets.map((item) => {
        const target = asRecord(item);
        return {
          target: readString(target.target, 'unknown'),
          reasonCode: readString(target.reasonCode, 'UNKNOWN'),
        };
      })
    : [];
  return {
    status: readString(root.status, 'conditional'),
    claimSet: readString(root.claimSet, 'source-local-install'),
    claimedTargets: readStringArray(root.claimedTargets),
    notEvidencedTargets: readStringArray(root.notEvidencedTargets),
    blockedTargets,
    allowedClaims: readStringArray(root.releaseNotesAllowedClaims),
  };
}

export function mapTargetClosureActions(payload: unknown): TargetClosureActionViewModel[] {
  const values = Array.isArray(payload) ? payload : [];
  return values.map((item) => {
    const action = asRecord(item);
    return {
      target: readString(action.target, 'unknown'),
      status: readString(action.status, 'not_evidenced'),
      recommendedPath: readString(action.recommendedPath, 'manual_local'),
      commands: readStringArray(action.commands),
      runbook: readString(action.runbook, ''),
      reasonCodes: readStringArray(action.reasonCodes),
    };
  });
}

