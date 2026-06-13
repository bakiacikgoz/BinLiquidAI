import { OperatorAttestationCard } from './OperatorAttestationCard';
import { mapTargetEvidenceClosure, targetEvidenceBadges } from './targetEvidenceMappers';
import type { TargetEvidenceClosureSummary } from './targetEvidenceTypes';

export function TargetEvidenceClosure({
  closure,
}: {
  closure?: TargetEvidenceClosureSummary | null;
}) {
  const summary = mapTargetEvidenceClosure(closure);
  const claims = summary.blockedClaims.length > 0 ? summary.blockedClaims : ['public/live boundaries pending'];

  return (
    <article className="page-card provider-trust-surface target-evidence-closure">
      <div className="page-card-header">
        <div>
          <h3>Target Evidence Closure</h3>
          <p>
            {summary.status} · {summary.mode ?? 'mode pending'} · {summary.generatedAtUtc}
          </p>
        </div>
      </div>
      <div className="reason-list" aria-label="Target evidence safety badges">
        {targetEvidenceBadges(summary).map((badge) => (
          <span className="reason-chip" data-tone={badge.tone} key={badge.label}>
            {badge.label}
          </span>
        ))}
      </div>
      <section className="run-list-item">
        <strong>Blocked claim boundaries</strong>
        <div className="reason-list" aria-label="Blocked target evidence claims">
          {claims.map((claim) => (
            <span className="reason-chip" key={claim}>
              {claim}
            </span>
          ))}
        </div>
      </section>
      <OperatorAttestationCard closure={summary} />
    </article>
  );
}
