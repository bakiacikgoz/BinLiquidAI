import { screen, within } from '@testing-library/react';
import type { UserEvent } from '@testing-library/user-event';

export async function navigateByButton(user: UserEvent, name: string | RegExp): Promise<void> {
  await user.click(screen.getByRole('button', { name }));
}

export async function fillTextbox(user: UserEvent, name: string | RegExp, value: string): Promise<void> {
  const input = screen.getByRole('textbox', { name });
  await user.clear(input);
  await user.type(input, value);
}

export async function chooseOption(user: UserEvent, name: string | RegExp, value: string): Promise<void> {
  await user.selectOptions(screen.getByRole('combobox', { name }), value);
}

export async function clickWithin(
  user: UserEvent,
  regionName: string | RegExp,
  buttonName: string | RegExp,
): Promise<void> {
  const region = screen.getByRole('region', { name: regionName });
  await user.click(within(region).getByRole('button', { name: buttonName }));
}
