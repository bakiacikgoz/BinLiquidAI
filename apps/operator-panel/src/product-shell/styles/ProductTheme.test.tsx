import { cleanup, render } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { ProductTheme } from './ProductTheme';

const { setTheme } = vi.hoisted(() => ({ setTheme: vi.fn().mockResolvedValue(undefined) }));
vi.mock('@tauri-apps/api/window', () => ({ getCurrentWindow: () => ({ setTheme }) }));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.clearAllMocks();
  Reflect.deleteProperty(window, '__TAURI_INTERNALS__');
});

it('synchronizes native material with the product theme and cleans up transparent roots', () => {
  Object.defineProperty(window, '__TAURI_INTERNALS__', { configurable: true, value: {} });
  vi.spyOn(navigator, 'platform', 'get').mockReturnValue('MacIntel');
  const view = render(<ProductTheme theme="dark" />);
  expect(setTheme).toHaveBeenLastCalledWith('dark');
  expect(document.documentElement).toHaveClass('product-native-mac');
  view.rerender(<ProductTheme theme="light" />);
  expect(setTheme).toHaveBeenLastCalledWith('light');
  view.unmount();
  expect(document.documentElement).not.toHaveClass('product-native-mac');
});

it('keeps browser preview opaque even on macOS', () => {
  vi.spyOn(navigator, 'platform', 'get').mockReturnValue('MacIntel');
  render(<ProductTheme theme="dark" />);
  expect(setTheme).not.toHaveBeenCalled();
  expect(document.documentElement).not.toHaveClass('product-native-mac');
});
