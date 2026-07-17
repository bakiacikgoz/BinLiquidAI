import type { AssistantArtifactProposalPart } from '../../assistant/assistantTypes';
import { Button } from '../primitives/Button';

export function ArtifactProposalCard({
  proposal,
  disabled,
  disabledReason,
  onReview,
  onApprove,
  onReject,
  onApply,
}: {
  proposal: AssistantArtifactProposalPart;
  disabled: boolean;
  disabledReason: string;
  onReview: (approvalId: string) => void;
  onApprove: (approvalId: string) => void;
  onReject: (approvalId: string) => void;
  onApply: (proposal: AssistantArtifactProposalPart) => void;
}) {
  const decisionDisabled = disabled || proposal.status !== 'pending';
  const executeDisabled = disabled || proposal.status !== 'approved';

  return (
    <section className="assistant-artifact-proposal" aria-label="Artifact proposal">
      <div className="assistant-artifact-proposal-heading">
        <div>
          <strong>{proposal.title}</strong>
          <p>{proposal.kind} proposal · revision {proposal.baseRevisionNumber}</p>
        </div>
        <span>{proposal.status}</span>
      </div>
      <p>{proposal.summary}</p>
      {proposal.error ? <p role="alert" className="assistant-error-text">{proposal.error.slice(0, 500)}</p> : null}
      <div className="assistant-artifact-proposal-actions">
        <Button variant="secondary" onClick={() => onReview(proposal.approvalId)}>
          Review proposal approval
        </Button>
        {proposal.status === 'pending' ? (
          <>
            <Button disabled={decisionDisabled} title={decisionDisabled ? disabledReason : undefined} onClick={() => onApprove(proposal.approvalId)}>
              Approve proposal
            </Button>
            <Button variant="danger" disabled={decisionDisabled} title={decisionDisabled ? disabledReason : undefined} onClick={() => onReject(proposal.approvalId)}>
              Reject proposal
            </Button>
          </>
        ) : null}
        {proposal.status === 'approved' ? (
          <Button disabled={executeDisabled} title={executeDisabled ? disabledReason : undefined} onClick={() => onApply(proposal)}>
            Apply approved proposal
          </Button>
        ) : null}
      </div>
    </section>
  );
}
