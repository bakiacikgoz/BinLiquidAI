import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';

import { renderOperatorPanel } from '../../test/render';
import { ApprovalGateCard } from './ApprovalGateCard';

describe('ApprovalGateCard interactions', () => {
  it('calls approval callbacks when approval mutations are available', async () => {
    const onApprove = vi.fn();
    const onEdit = vi.fn();
    const onReject = vi.fn();
    const { user } = renderOperatorPanel(
      <ApprovalGateCard
        hasApproval
        disabled={false}
        disabledReason=""
        approvalLabel="Review supervised action."
        onApprove={onApprove}
        onEdit={onEdit}
        onReject={onReject}
      />,
    );

    await user.click(screen.getByRole('button', { name: /Onayla ve Devam Et/i }));
    await user.click(screen.getByRole('button', { name: /Düzenle/i }));
    await user.click(screen.getByRole('button', { name: /Reddet/i }));

    expect(onApprove).toHaveBeenCalledTimes(1);
    expect(onEdit).toHaveBeenCalledTimes(1);
    expect(onReject).toHaveBeenCalledTimes(1);
  });

  it('keeps approval mutations disabled and visible when operator context blocks them', async () => {
    const onApprove = vi.fn();
    const onReject = vi.fn();
    const { user } = renderOperatorPanel(
      <ApprovalGateCard
        hasApproval
        disabled
        disabledReason="Operator ID is required."
        approvalLabel="Review supervised action."
        onApprove={onApprove}
        onEdit={vi.fn()}
        onReject={onReject}
      />,
    );

    expect(screen.getByText('Operator ID is required.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Onayla ve Devam Et/i }));
    await user.click(screen.getByRole('button', { name: /Reddet/i }));

    expect(onApprove).not.toHaveBeenCalled();
    expect(onReject).not.toHaveBeenCalled();
  });
});
