import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SETTINGS_KEY, DEFAULT_SETTINGS } from '../../settings';
import { useAssistantModels } from '../../assistant/useAssistantModels';
import { renderOperatorPanel } from '../../test/render';
import { useProductShellStore } from '../state/productShellStore';
import { SettingsShell } from './SettingsShell';

vi.mock('../../assistant/useAssistantModels', async (original) => ({
  ...await original<typeof import('../../assistant/useAssistantModels')>(), useAssistantModels: vi.fn(),
}));

beforeEach(() => {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify({ ...DEFAULT_SETTINGS, locale: 'en' }));
  useProductShellStore.setState({ theme: 'dark' });
  vi.mocked(useAssistantModels).mockReturnValue({ status: 'empty', models: [], providers: [], response: null, error: null, refresh: vi.fn() });
});

describe('SettingsShell', () => {
  it('persists operator settings and applies the selected product theme', async () => {
    const { user } = renderOperatorPanel(<SettingsShell />);
    await user.clear(screen.getByRole('textbox', { name: 'Operator identity' }));
    await user.type(screen.getByRole('textbox', { name: 'Operator identity' }), 'release-operator');
    await user.click(screen.getByRole('button', { name: 'Appearance' }));
    await user.selectOptions(screen.getByRole('combobox', { name: 'Theme' }), 'light');
    await user.click(screen.getByRole('button', { name: 'Save settings' }));
    expect(JSON.parse(localStorage.getItem(SETTINGS_KEY) ?? '{}')).toMatchObject({ operatorId: 'release-operator', theme: 'light' });
    expect(useProductShellStore.getState().theme).toBe('light');
  });

  it('maps settings sections to content and leaves Cmd-K to global search', async () => {
    const { user } = renderOperatorPanel(<SettingsShell />);
    const search = screen.getByRole('textbox', { name: 'Search settings' });
    await user.click(screen.getByRole('button', { name: 'Assistant' }));
    expect(screen.getByRole('textbox', { name: 'Assistant profile' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Default approval profile' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Shortcuts' }));
    expect(screen.getByText('⌘/Ctrl K')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Security' })).toHaveAttribute('href', '#/system/settings');
    await user.keyboard('{Meta>}k{/Meta}');
    expect(search).not.toHaveFocus();
  });

  it('finds model settings by field name and reports an unmatched query', async () => {
    const { user } = renderOperatorPanel(<SettingsShell />);
    const search = screen.getByRole('textbox', { name: 'Search settings' });
    await user.type(search, 'model');
    await user.click(screen.getByRole('button', { name: 'Assistant' }));
    expect(screen.getByRole('combobox', { name: 'Model' })).toBeInTheDocument();
    await user.clear(search);
    await user.type(search, 'zzzzzz');
    expect(screen.getByText('No settings found.')).toHaveAttribute('role', 'status');
  });

  it('saves a discovered model and keeps unavailable models disabled', async () => {
    const refresh = vi.fn();
    vi.mocked(useAssistantModels).mockReturnValue({ status: 'success', response: null, error: null, refresh, providers: [], models: [
      { provider: 'local-transformers', id: 'cached-model', displayName: 'Cached model', installed: true, configured: false, source: 'transformers_cache', warnings: [] },
      { provider: 'ollama', id: 'missing-model', displayName: 'Missing model', installed: false, configured: false, source: 'ollama', warnings: [] },
    ] });
    const { user } = renderOperatorPanel(<SettingsShell />);
    await user.click(screen.getByRole('button', { name: 'AI providers' }));
    expect(screen.getByRole('option', { name: /Missing model/ })).toBeDisabled();
    await user.selectOptions(screen.getByRole('combobox', { name: 'Model' }), JSON.stringify(['local-transformers', 'cached-model']));
    await user.click(screen.getByRole('button', { name: 'Save settings' }));
    expect(JSON.parse(localStorage.getItem(SETTINGS_KEY) ?? '{}')).toMatchObject({ assistantProvider: 'local-transformers', assistantModel: '', assistantHfModelId: 'cached-model' });
    await user.click(screen.getByRole('button', { name: 'Refresh models' }));
    expect(refresh).toHaveBeenCalledOnce();
  });

  it('shows a recovery action when discovery fails and preserves the configured model', async () => {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify({ ...DEFAULT_SETTINGS, locale: 'tr', assistantProvider: 'ollama', assistantModel: 'saved-model' }));
    vi.mocked(useAssistantModels).mockReturnValue({ status: 'error', response: null, models: [], providers: [], error: { code: 'OFFLINE', message: 'connection refused' }, refresh: vi.fn() });
    const { user } = renderOperatorPanel(<SettingsShell />);
    await user.click(screen.getByRole('button', { name: 'AI Sağlayıcıları' }));
    expect(screen.getByRole('combobox', { name: 'Model' })).toHaveDisplayValue('saved-model · Kullanılamıyor');
    expect(screen.getByRole('link', { name: 'Sağlayıcıları yapılandır' })).toHaveAttribute('href', '#/system/settings');
    expect(screen.getByText('connection refused').closest('details')).not.toHaveAttribute('open');
  });
});
