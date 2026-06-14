import type { DesignPartnerFieldEvidenceSnapshot, FieldEvidenceBadge } from './designPartnerFieldTypes';

export function mapDesignPartnerFieldEvidence(
  snapshot?: DesignPartnerFieldEvidenceSnapshot | null,
): DesignPartnerFieldEvidenceSnapshot {
  return (
    snapshot ?? {
      schemaVersion: 'control-plane.design-partner-field-evidence/v1',
      generatedAtUtc: new Date(0).toISOString(),
      status: 'missing',
      mode: null,
      sessionId: null,
      evidenceMode: 'hash_only',
      rawPersistence: false,
      attestationStatus: 'missing',
      strictRcStatus: 'missing',
      itemCount: 0,
      blockedClaims: [],
      latestBundlePath: null,
      latestAttestationPath: null,
      latestPromotionPath: null,
      blockingReasons: [],
      warnings: ['FIELD_EVIDENCE_NOT_COLLECTED'],
    }
  );
}

export function fieldEvidenceBadges(snapshot: DesignPartnerFieldEvidenceSnapshot): FieldEvidenceBadge[] {
  return [
    { label: snapshot.evidenceMode, tone: snapshot.evidenceMode === 'hash_only' ? 'ready' : 'neutral' },
    { label: snapshot.rawPersistence ? 'raw_persistence_on' : 'raw_persistence_off', tone: snapshot.rawPersistence ? 'blocked' : 'ready' },
    { label: `attestation_${snapshot.attestationStatus}`, tone: snapshot.attestationStatus === 'valid' ? 'ready' : 'warning' },
    { label: `strict_rc_${snapshot.strictRcStatus}`, tone: snapshot.strictRcStatus === 'ready' ? 'ready' : snapshot.strictRcStatus === 'blocked' ? 'blocked' : 'warning' },
    { label: snapshot.status, tone: snapshot.status === 'ready' ? 'ready' : snapshot.status === 'blocked' ? 'blocked' : 'warning' },
  ];
}
