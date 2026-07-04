import { asControlPlaneClaimMatrix } from '../../controlPlaneMappers';
import type { UiLocale } from '../../i18n';
import { ReasonChip, StatusBadge } from '../primitives/Token';

const copy = {
  en: {
    claimGuard: 'Claim Guard',
    unsupportedBlocked: (count: number) => `${count} unsupported claim blocked`,
    noBlockedClaims: 'No blocked claims',
    noBlockingReason: 'No blocking reason',
    computerUseBoundary: 'Live computer-use qualification-gated.',
    macosQualification:
      'macOS live qualification requires explicit opt-in, Screen Recording, Accessibility, provider readiness and replay evidence.',
    blocked: 'blocked',
  },
  tr: {
    claimGuard: 'Claim koruması',
    unsupportedBlocked: (count: number) => `${count} desteklenmeyen claim blokelendi`,
    noBlockedClaims: 'Blokelenen claim yok',
    noBlockingReason: 'Bloklama nedeni yok',
    computerUseBoundary: 'Live computer-use qualification-gated.',
    macosQualification:
      'macOS live qualification requires explicit opt-in, Screen Recording, Accessibility, provider readiness and replay evidence.',
    blocked: 'bloke',
  },
} satisfies Record<UiLocale, {
  claimGuard: string;
  unsupportedBlocked: (count: number) => string;
  noBlockedClaims: string;
  noBlockingReason: string;
  computerUseBoundary: string;
  macosQualification: string;
  blocked: string;
}>;

export function ClaimBoundaryBanner({ claims, locale = 'en' }: { claims: unknown; locale?: UiLocale }) {
  const text = copy[locale];
  const matrix = asControlPlaneClaimMatrix(claims);
  const blocked = matrix.claims.filter((claim) => claim.status === 'blocked');
  return (
    <article className="page-card">
      <h3>{text.claimGuard}</h3>
      <p className="workspace-lead">
        {blocked.length > 0 ? text.unsupportedBlocked(blocked.length) : text.noBlockedClaims}
      </p>
      <p className="workspace-lead">{text.computerUseBoundary}</p>
      <p className="workspace-lead">{text.macosQualification}</p>
      <div className="run-list">
        {matrix.claims.map((claim) => (
          <article className="run-list-item" key={claim.claim_id}>
            <div className="run-list-main">
              <strong>{claim.claim_id}</strong>
              <div className="run-list-meta">
                {claim.blocking_reasons.length > 0 ? (
                  claim.blocking_reasons.map((reason) => <ReasonChip key={reason}>{reason}</ReasonChip>)
                ) : (
                  <span>{text.noBlockingReason}</span>
                )}
              </div>
            </div>
            <StatusBadge tone={claim.status === 'blocked' ? 'error' : 'success'}>
              {claim.status === 'blocked' ? text.blocked : claim.status}
            </StatusBadge>
          </article>
        ))}
      </div>
    </article>
  );
}
