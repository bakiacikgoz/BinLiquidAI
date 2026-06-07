import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';

import { renderOperatorPanel } from '../../test/render';
import { TopControls } from './TopControls';

describe('TopControls interactions', () => {
  it('calls nav and refresh actions', async () => {
    const onToggleNav = vi.fn();
    const onRefresh = vi.fn();
    const { user } = renderOperatorPanel(
      <TopControls
        previewMode
        operatorWarning=""
        contractWarning=""
        onToggleNav={onToggleNav}
        onCycleTheme={vi.fn()}
        onRefresh={onRefresh}
      />,
    );

    await user.click(screen.getByRole('button', { name: /Navigasyonu aç/i }));
    await user.click(screen.getByRole('button', { name: /Yenile/i }));

    expect(onToggleNav).toHaveBeenCalledTimes(1);
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });
});
