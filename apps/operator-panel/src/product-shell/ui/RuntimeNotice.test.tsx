import { render, screen } from '@testing-library/react';
import { afterEach, expect, it } from 'vitest';
import { RuntimeNotice } from './RuntimeNotice';

afterEach(() => { Reflect.deleteProperty(window, '__TAURI_INTERNALS__'); });
it('labels browser sample data without implying a live desktop connection', () => {
  render(<RuntimeNotice />);
  expect(screen.getByRole('status')).toHaveTextContent(/Preview|Önizleme/);
  expect(screen.getByRole('status')).toHaveTextContent(/Sample data|örnek veri/);
});
it('does not label the native app as a preview', () => {
  Object.defineProperty(window, '__TAURI_INTERNALS__', { value: {}, configurable: true });
  const { container } = render(<RuntimeNotice />);
  expect(container).toBeEmptyDOMElement();
});
