import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';

import { renderOperatorPanel } from '../../test/render';
import { NotificationStack } from './NotificationStack';

describe('NotificationStack interactions', () => {
  it('dismisses the selected notification by id', async () => {
    const onDismiss = vi.fn();
    const { user } = renderOperatorPanel(
      <NotificationStack
        items={[
          {
            id: 'approval',
            kind: 'warning',
            title: 'Approval requested',
            subtitle: 'Waiting for operator.',
            time: 'now',
          },
        ]}
        onDismiss={onDismiss}
      />,
    );

    await user.click(screen.getByRole('button', { name: /Bildirimi kapat/i }));

    expect(onDismiss).toHaveBeenCalledWith('approval');
  });
});
