import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';

import { renderOperatorPanel } from '../../test/render';
import { RuntimeSummaryCard } from './RuntimeSummaryCard';

describe('RuntimeSummaryCard interactions', () => {
  it('keeps raw payload disclosure disabled when debug raw is off', async () => {
    const onRawJsonRequested = vi.fn();
    const { user } = renderOperatorPanel(
      <RuntimeSummaryCard
        items={[{ id: 'summary', tone: 'success', text: 'Runtime ok.' }]}
        rawJson={{ token: 'secret-token' }}
        debugRawEnabled={false}
        onRawJsonRequested={onRawJsonRequested}
      />,
    );

    await user.click(screen.getByRole('button', { name: /Ham JSON'u Görüntüle/i }));

    expect(onRawJsonRequested).not.toHaveBeenCalled();
    expect(screen.queryByText(/secret-token/i)).not.toBeInTheDocument();
  });

  it('requires explicit confirmation before showing redacted raw payload', async () => {
    const onRawJsonRequested = vi.fn(() => true);
    const { user } = renderOperatorPanel(
      <RuntimeSummaryCard
        items={[{ id: 'summary', tone: 'success', text: 'Runtime ok.' }]}
        rawJson={{ token: 'secret-token', status: 'ok' }}
        debugRawEnabled
        onRawJsonRequested={onRawJsonRequested}
      />,
    );

    await user.click(screen.getByRole('button', { name: /Ham JSON'u Görüntüle/i }));

    expect(onRawJsonRequested).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/"status": "ok"/i)).toBeInTheDocument();
    expect(screen.queryByText(/secret-token/i)).not.toBeInTheDocument();
  });
});
