import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import { SETTINGS_KEY } from '../../settings';
import { renderOperatorPanel } from '../../test/render';
import { useProductShellStore } from '../state/productShellStore';
import { SettingsShell } from './SettingsShell';

describe('SettingsShell', () => {
  beforeEach(() => {
    localStorage.removeItem(SETTINGS_KEY);
    useProductShellStore.setState({ theme: 'dark' });
  });

  it('persists operator settings and applies the selected product theme', async () => {
    const { user } = renderOperatorPanel(<SettingsShell />);

    await user.clear(screen.getByRole('textbox', { name: 'Operator identity' }));
    await user.type(screen.getByRole('textbox', { name: 'Operator identity' }), 'release-operator');
    await user.selectOptions(screen.getByRole('combobox', { name: 'Theme' }), 'light');
    await user.click(screen.getByRole('button', { name: 'Save settings' }));

    expect(JSON.parse(localStorage.getItem(SETTINGS_KEY) ?? '{}')).toMatchObject({ operatorId: 'release-operator', theme: 'light' });
    expect(useProductShellStore.getState().theme).toBe('light');
  });
});
