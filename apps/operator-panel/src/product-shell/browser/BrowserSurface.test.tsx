import { screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const invoke = vi.hoisted(() => vi.fn());

vi.mock('@tauri-apps/api/core', () => ({ invoke }));

import { renderOperatorPanel } from '../../test/render';
import { BrowserSurface } from './BrowserSurface';

describe('BrowserSurface', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    invoke.mockImplementation(async (command: string) => {
      if (command === 'browser_open') return 'imperaos-browser-user';
      if (command === 'browser_history_state') return { canBack: true, canForward: false };
      return undefined;
    });
  });

  it('sends history navigation back through the native governed session', async () => {
    const { user, container } = renderOperatorPanel(<BrowserSurface onClose={vi.fn()} />);

    expect(container.querySelector('.browser-surface .browser-toolbar .browser-address-bar')).toBeInTheDocument();
    expect(container.querySelector('.browser-page.native-browser-viewport')).toBeInTheDocument();
    await user.clear(screen.getByRole('textbox', { name: 'Browser address' }));
    await user.type(screen.getByRole('textbox', { name: 'Browser address' }), 'https://imperaos.dev/docs');
    await user.click(screen.getByRole('button', { name: 'Open HTTPS' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Back' })).toBeEnabled());
    await user.click(screen.getByRole('button', { name: 'Back' }));

    expect(invoke).toHaveBeenCalledWith('browser_back', {
      request: { label: 'imperaos-browser-user' },
    });
  });

  it('synchronizes the native child webview to the reserved viewport', async () => {
    const bounds = vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
      x: 120, y: 180, width: 740, height: 420, top: 180, right: 860, bottom: 600, left: 120,
      toJSON: () => ({}),
    });
    const { user } = renderOperatorPanel(<BrowserSurface onClose={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: 'Open HTTPS' }));

    await waitFor(() => expect(invoke).toHaveBeenCalledWith('browser_set_bounds', {
      request: { label: 'imperaos-browser-user', x: 120, y: 180, width: 740, height: 420 },
    }));
    bounds.mockRestore();
  });
});
