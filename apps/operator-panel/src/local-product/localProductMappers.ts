import type { LocalProductReadinessViewModel, PlatformTargetViewModel } from './localProductTypes';

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}

function readString(source: Record<string, unknown>, key: string, fallback = ''): string {
  const value = source[key];
  return typeof value === 'string' ? value : fallback;
}

function readBool(source: Record<string, unknown>, key: string): boolean {
  return source[key] === true;
}

function readStringArray(source: Record<string, unknown>, key: string): string[] {
  const value = source[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

export function mapLocalProductReadiness(payload: unknown): LocalProductReadinessViewModel {
  const record = asRecord(payload);
  const target = asRecord(record.target);
  const claimBoundary = asRecord(record.claimBoundary);
  const currentTarget: PlatformTargetViewModel = {
    os: readString(target, 'os', 'unknown'),
    arch: readString(target, 'arch', 'unknown'),
    targetId: readString(target, 'targetId', 'unknown-unknown'),
    supportTier: readString(target, 'supportTier', 'unsupported'),
    claimAllowed: readBool(target, 'claimAllowed') || readBool(claimBoundary, 'claimAllowed'),
    reasonCodes: readStringArray(target, 'reasonCodes'),
  };
  return {
    schemaVersion: readString(record, 'schemaVersion', 'local_product_readiness/v1'),
    overallStatus: readString(record, 'overallStatus', 'blocked'),
    currentTarget,
    supportedClaims: readStringArray(claimBoundary, 'supportedClaims'),
    notEvidencedTargets: readStringArray(claimBoundary, 'notEvidencedTargets'),
    unsupportedTargets: readStringArray(claimBoundary, 'unsupportedTargets'),
    blockedTargets: readStringArray(claimBoundary, 'blockedTargets'),
    productClaimSummary: readString(claimBoundary, 'productClaimSummary', ''),
    blockingReasons: readStringArray(claimBoundary, 'blockingReasons'),
  };
}

export function getTargetClaimBadge(
  target: PlatformTargetViewModel,
): 'supported' | 'experimental' | 'not-evidenced' | 'unsupported' | 'blocked' {
  if (target.claimAllowed) {
    return 'supported';
  }
  if (target.supportTier === 'experimental') {
    return 'experimental';
  }
  if (target.supportTier === 'supported') {
    return 'not-evidenced';
  }
  return 'unsupported';
}

