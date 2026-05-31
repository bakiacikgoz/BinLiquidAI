import { asControlPlaneClaimMatrix } from '../../controlPlaneMappers';

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
            <strong>{claim.claim_id}</strong>
            <span>{claim.status}</span>
            {claim.blocking_reasons.length > 0 ? <small>{claim.blocking_reasons.join(', ')}</small> : null}
          </article>
        ))}
      </div>
    </article>
  );
}
