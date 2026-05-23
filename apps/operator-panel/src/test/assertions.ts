import { expect, type Mock } from 'vitest';
import { screen } from '@testing-library/react';

export function expectDisabledWithReason(name: string | RegExp, reason: string | RegExp): void {
  const button = screen.getByRole('button', { name });
  expect(button).toBeDisabled();
  if (typeof reason === 'string') {
    expect(button).toHaveAttribute('title', expect.stringContaining(reason));
  } else {
    expect(button.getAttribute('title') ?? '').toMatch(reason);
  }
}

export function expectNoBridgeCall(mock: Mock): void {
  expect(mock).not.toHaveBeenCalled();
}

export function expectBridgeCall(mock: Mock, command: string): void {
  expect(mock).toHaveBeenCalledWith(command, expect.any(Object));
}

export function expectSafeErrorMessage(message: string | RegExp): void {
  expect(screen.getByText(message)).toBeInTheDocument();
}
