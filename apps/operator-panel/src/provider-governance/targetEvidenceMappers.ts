import type { TargetEvidenceBadge, TargetEvidenceClosureSummary } from './targetEvidenceTypes';

export function mapTargetEvidenceClosure(
  summary?: TargetEvidenceClosureSummary | null,
): TargetEvidenceClosureSummary {
  return (
    summary ?? {
      contractVersion: 'control-plane.target-evidence-closure/v1',
      generatedAtUtc: new Date(0).toISOString(),
      status: 'unknown',
      sessionId: null,
      mode: null,
      evidenceMode: null,
      rawPersistence: false,
      blockingReasons: [],
      warnings: ['TARGET_EVIDENCE_NOT_COLLECTED'],
      blockedClaims: [],
      attestationStatus: 'missing',
    }
  );
}

export function targetEvidenceBadges(summary: TargetEvidenceClosureSummary): TargetEvidenceBadge[] {
  const badges: TargetEvidenceBadge[] = [
    { label: summary.evidenceMode ?? 'hash_only_pending', tone: summary.evidenceMode === 'hash_only' ? 'ready' : 'neutral' },
    { label: summary.rawPersistence ? 'raw_persistence_on' : 'raw_persistence_off', tone: summary.rawPersistence ? 'blocked' : 'ready' },
    { label: `attestation_${summary.attestationStatus}`, tone: summary.attestationStatus === 'missing' ? 'warning' : 'ready' },
  ];
  if (summary.status === 'blocked') {
    badges.push({ label: 'blocked', tone: 'blocked' });
  }
  if (summary.status === 'conditional' || summary.status === 'unknown') {
    badges.push({ label: summary.status, tone: 'warning' });
  }
  return badges;
}
