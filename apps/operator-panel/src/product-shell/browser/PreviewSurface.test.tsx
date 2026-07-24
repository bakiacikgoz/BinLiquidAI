import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

const invoke = vi.hoisted(() => vi.fn());

vi.mock('@tauri-apps/api/core', () => ({ invoke }));

import { renderOperatorPanel } from '../../test/render';
import { PreviewSurface } from './PreviewSurface';

describe('PreviewSurface', () => {
  it('owns and closes its registered native preview session', async () => {
    invoke.mockImplementation(async (command: string) => {
      if (command === 'browser_list_preview_origins') return ['http://localhost:5173'];
      if (command === 'browser_open') return 'imperaos-browser-preview';
      if (command === 'browser_history_state') return { canBack: false, canForward: false };
      return undefined;
    });
    const onClose = vi.fn();
    const { user } = renderOperatorPanel(<PreviewSurface onClose={onClose} />);

    await screen.findByRole('option', { name: 'http://localhost:5173' });
    await user.click(screen.getByRole('button', { name: 'Open preview' }));
    await user.click(screen.getByRole('button', { name: 'Close' }));

    expect(invoke).toHaveBeenCalledWith('browser_open', {
      request: { mode: 'preview', url: 'http://localhost:5173' },
    });
    expect(invoke).toHaveBeenCalledWith('browser_close', {
      request: { label: 'imperaos-browser-preview' },
    });
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
