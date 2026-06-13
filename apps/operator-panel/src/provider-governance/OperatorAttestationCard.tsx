import type { TargetEvidenceClosureSummary } from './targetEvidenceTypes';

export function OperatorAttestationCard({
  closure,
}: {
  closure: TargetEvidenceClosureSummary;
}) {
  return (
    <section className="run-list-item">
      <strong>Operator Attestation</strong>
      <span>{closure.attestationStatus}</span>
      <small>{closure.sessionId ?? 'session pending'}</small>
    </section>
  );
}
