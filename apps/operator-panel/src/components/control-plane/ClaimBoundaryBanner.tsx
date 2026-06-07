import { asControlPlaneClaimMatrix } from '../../controlPlaneMappers';
import { ReasonChip, StatusBadge } from '../primitives/Token';

export function ClaimBoundaryBanner({ claims }: { claims: unknown }) {
  const matrix = asControlPlaneClaimMatrix(claims);
  const blocked = matrix.claims.filter((claim) => claim.status === 'blocked');
  return (
    <article className="page-card">
      <h3>Claim Guard</h3>
      <p className="workspace-lead">
        {blocked.length > 0 ? `${blocked.length} unsupported claim blocked` : 'No blocked claims'}
      </p>
      <div className="run-list">
        {matrix.claims.map((claim) => (
          <article className="run-list-item" key={claim.claim_id}>
            <div className="run-list-main">
              <strong>{claim.claim_id}</strong>
              <div className="run-list-meta">
                {claim.blocking_reasons.length > 0 ? (
                  claim.blocking_reasons.map((reason) => <ReasonChip key={reason}>{reason}</ReasonChip>)
                ) : (
                  <span>No blocking reason</span>
                )}
              </div>
            </div>
            <StatusBadge tone={claim.status === 'blocked' ? 'error' : 'success'}>{claim.status}</StatusBadge>
          </article>
        ))}
      </div>
    </article>
  );
}
