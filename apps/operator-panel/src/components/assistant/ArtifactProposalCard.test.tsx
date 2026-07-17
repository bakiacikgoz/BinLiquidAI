import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { renderOperatorPanel } from '../../test/render';
import { ArtifactProposalCard } from './ArtifactProposalCard';

const proposal = {
  type: 'artifact-proposal' as const,
  proposalId: 'proposal-1',
  artifactId: 'artifact-1',
  approvalId: 'approval-1',
  actionHash: 'a'.repeat(64),
  baseRevisionNumber: 1,
  title: 'Operations plan update',
  kind: 'document',
  summary: 'Update the opening paragraph',
  status: 'pending' as const,
  error: null,
};

describe('ArtifactProposalCard', () => {
  it('exposes review, approve and reject actions without raw proposal JSON', async () => {
    const onReview = vi.fn();
    const onApprove = vi.fn();
    const onReject = vi.fn();
    const { user } = renderOperatorPanel(
      <ArtifactProposalCard
        proposal={proposal}
        disabled={false}
        disabledReason=""
        onReview={onReview}
        onApprove={onApprove}
        onReject={onReject}
        onApply={vi.fn()}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Review proposal approval' }));
    await user.click(screen.getByRole('button', { name: 'Approve proposal' }));
    await user.click(screen.getByRole('button', { name: 'Reject proposal' }));

    expect(onReview).toHaveBeenCalledWith('approval-1');
    expect(onApprove).toHaveBeenCalledWith('approval-1');
    expect(onReject).toHaveBeenCalledWith('approval-1');
    expect(screen.queryByText(/\{"/)).not.toBeInTheDocument();
  });

  it('applies the exact governed proposal only after approval and renders bounded failure state', async () => {
    const onApply = vi.fn();
    const { user } = renderOperatorPanel(
      <ArtifactProposalCard
        proposal={{ ...proposal, status: 'approved', error: 'Revision changed before apply.' }}
        disabled={false}
        disabledReason=""
        onReview={vi.fn()}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onApply={onApply}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Apply approved proposal' }));
    expect(onApply).toHaveBeenCalledWith({ ...proposal, status: 'approved', error: 'Revision changed before apply.' });
    expect(screen.getByRole('alert')).toHaveTextContent('Revision changed before apply.');
  });
});
