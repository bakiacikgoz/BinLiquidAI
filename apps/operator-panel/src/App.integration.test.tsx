import { screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import App from './App';
import * as bridge from './bridge';
import { renderOperatorPanel } from './test/render';
import { DEFAULT_SETTINGS, SETTINGS_KEY, type PanelSettings } from './settings';

vi.mock('./bridge', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./bridge')>();
  return {
    ...actual,
    checkPermission: vi.fn(actual.checkPermission),
    decideApproval: vi.fn(actual.decideApproval),
    executeApproval: vi.fn(actual.executeApproval),
    exportRunArtifacts: vi.fn(actual.exportRunArtifacts),
    fetchIdentity: vi.fn(actual.fetchIdentity),
    resolveConfig: vi.fn(actual.resolveConfig),
    submitComputerUseRun: vi.fn(actual.submitComputerUseRun),
    submitTeamRun: vi.fn(actual.submitTeamRun),
  };
});

function seedSettings(overrides: Partial<PanelSettings> = {}) {
  localStorage.setItem(
    SETTINGS_KEY,
    JSON.stringify({
      ...DEFAULT_SETTINGS,
      locale: 'en',
      rootDir: '.binliquid/test-ui/jobs',
      ...overrides,
    }),
  );
}

function renderApp(overrides: Partial<PanelSettings> = {}) {
  seedSettings(overrides);
  return renderOperatorPanel(<App />);
}

async function openView(user: ReturnType<typeof renderOperatorPanel>['user'], navName: string | RegExp) {
  await user.click(screen.getByRole('button', { name: navName }));
}

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  vi.spyOn(window, 'prompt').mockReturnValue('./exports/run-preview');
});

describe('App integration flows', () => {
  it('navigates the primary operator views in browser preview mode', async () => {
    const { user } = renderApp();

    expect(await screen.findByRole('heading', { name: 'Mission Control' })).toBeInTheDocument();
    expect(screen.getByText('Preview')).toBeInTheDocument();

    await openView(user, 'Görevler');
    expect(screen.getByRole('heading', { name: 'Tasks' })).toBeInTheDocument();

    await openView(user, 'Onaylar');
    expect(screen.getByRole('heading', { name: 'Approvals' })).toBeInTheDocument();

    await openView(user, 'Çalıştırmalar');
    expect(screen.getByRole('heading', { name: 'Runs' })).toBeInTheDocument();

    await openView(user, 'Sistem Sağlığı');
    expect(screen.getByRole('heading', { name: 'System' })).toBeInTheDocument();

    await openView(user, 'Yürütmeler');
    expect(screen.getByRole('heading', { name: 'Operations' })).toBeInTheDocument();

    await openView(user, 'Ayarlar');
    expect(screen.getByRole('heading', { name: 'Settings' })).toBeInTheDocument();
  });

  it('submits a team run through the preview bridge and returns to workspace', async () => {
    const { user } = renderApp({ operatorId: 'qa-operator' });

    await openView(user, 'Görevler');
    await user.type(screen.getByLabelText('Spec path'), 'examples/team/restricted_pilot.yaml');
    await user.type(screen.getByLabelText('Request'), 'Inspect the queue safely.');
    await user.click(screen.getAllByRole('button', { name: 'Submit run' })[0]);

    await waitFor(() => {
      expect(bridge.submitTeamRun).toHaveBeenCalledWith(
        expect.objectContaining({ operatorId: 'qa-operator' }),
        expect.objectContaining({
          specPath: 'examples/team/restricted_pilot.yaml',
          request: 'Inspect the queue safely.',
        }),
      );
    });
    expect(await screen.findByText('Submit run OK')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Mission Control' })).toBeInTheDocument();
  });

  it('keeps computer-use start fail-closed when the vision runtime is not qualified', async () => {
    const { user } = renderApp({ operatorId: 'qa-operator' });

    await openView(user, 'Görevler');
    const startButton = screen.getByRole('button', { name: 'Start session' });

    expect(startButton).toBeDisabled();
    expect(startButton.getAttribute('title') ?? '').toContain('Computer-use vision runtime blocked');
    await user.click(startButton);
    expect(bridge.submitComputerUseRun).not.toHaveBeenCalled();
  });

  it('executes the Mission Control approval CTA through explicit bridge args', async () => {
    const { user } = renderApp({ operatorId: 'qa-operator' });

    expect(await screen.findByRole('heading', { name: 'Mission Control' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Onayla ve Devam Et/i }));

    await waitFor(() => {
      expect(bridge.decideApproval).toHaveBeenCalledWith(
        expect.any(Object),
        'apr_20260308_device_action',
        true,
        'qa-operator',
        'mission control approval',
      );
      expect(bridge.executeApproval).toHaveBeenCalledWith(
        expect.any(Object),
        'apr_20260308_device_action',
        'qa-operator',
      );
    });
    expect(await screen.findByText('Onay akışı tamamlandı')).toBeInTheDocument();
  });

  it('disables approval mutations without operator id and approves with explicit confirmation when configured', async () => {
    const emptyOperator = renderApp();
    await openView(emptyOperator.user, 'Onaylar');
    expect(await screen.findByRole('button', { name: 'Approve' })).toBeDisabled();
    emptyOperator.unmount();

    const { user } = renderApp({ operatorId: 'qa-operator' });
    await openView(user, 'Onaylar');
    const approve = await screen.findByRole('button', { name: 'Approve' });

    await waitFor(() => expect(approve).not.toBeDisabled());
    await user.click(approve);

    await waitFor(() => {
      expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('ui:qa-operator'));
      expect(bridge.decideApproval).toHaveBeenCalledWith(
        expect.any(Object),
        'apr_20260308_device_action',
        true,
        'qa-operator',
        'operator workspace action',
      );
    });
    expect(await screen.findByText('Approve OK')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Execute' }));
    await waitFor(() => {
      expect(bridge.executeApproval).toHaveBeenCalledWith(
        expect.any(Object),
        'apr_20260308_device_action',
        'qa-operator',
      );
    });
    expect(await screen.findByText('Execute OK')).toBeInTheDocument();
  });

  it('requires debug raw and confirmation before exposing full artifact payloads', async () => {
    vi.mocked(window.confirm).mockReturnValue(false);
    const { user } = renderApp({ debugRaw: true });

    await openView(user, 'Çalıştırmalar');
    await user.click(await screen.findByRole('button', { name: 'Artifacts' }));
    const showRaw = await screen.findByRole('button', { name: 'Show raw' });

    await user.click(showRaw);
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('status.json'));
    expect(screen.getByRole('button', { name: 'Show raw' })).toBeInTheDocument();

    vi.mocked(window.confirm).mockReturnValue(true);
    await user.click(screen.getByRole('button', { name: 'Show raw' }));
    expect(await screen.findByRole('button', { name: 'Hide raw' })).toBeInTheDocument();
  });

  it('exports selected run artifacts with the prompt target passed to the bridge', async () => {
    const { user } = renderApp({ operatorId: 'qa-operator' });

    await openView(user, 'Çalıştırmalar');
    const exportButton = await screen.findByRole('button', { name: 'Export' });
    await waitFor(() => expect(exportButton).not.toBeDisabled());
    await user.click(exportButton);

    await waitFor(() => {
      expect(window.prompt).toHaveBeenCalledWith('Export directory', './exports/run_20260308_0910');
      expect(bridge.exportRunArtifacts).toHaveBeenCalledWith(
        expect.any(Object),
        'run_20260308_0910',
        './exports/run-preview',
      );
    });
    expect(await screen.findByText('Export completed')).toBeInTheDocument();
  });

  it('refreshes system config with assistant runtime override args', async () => {
    const { user } = renderApp({
      assistantProvider: 'ollama',
      assistantFallbackProvider: 'transformers',
      assistantModel: 'qwen3.5:4b',
    });

    await openView(user, 'Sistem Sağlığı');
    await user.click(screen.getByRole('button', { name: 'Refresh config' }));

    await waitFor(() => {
      expect(bridge.resolveConfig).toHaveBeenCalledWith(
        expect.objectContaining({ assistantProvider: 'ollama', assistantModel: 'qwen3.5:4b' }),
        expect.objectContaining({
          provider: 'ollama',
          fallbackProvider: 'transformers',
          model: 'qwen3.5:4b',
        }),
      );
    });
  });

  it('runs operations through preview bridge fixtures and persists settings changes', async () => {
    const { user } = renderApp({ operatorId: 'qa-operator' });

    await openView(user, 'Yürütmeler');
    await user.click(screen.getByRole('button', { name: 'Who am I' }));

    await waitFor(() => expect(bridge.fetchIdentity).toHaveBeenCalledWith(expect.any(Object)));
    expect((await screen.findAllByText(/qa-operator/)).length).toBeGreaterThan(0);
    await user.clear(screen.getByLabelText('Permission'));
    await user.type(screen.getByLabelText('Permission'), 'runtime.audit');
    await user.click(screen.getByRole('button', { name: 'Check permission' }));
    await waitFor(() => expect(bridge.checkPermission).toHaveBeenCalledWith(expect.any(Object), 'runtime.audit'));

    await openView(user, 'Ayarlar');
    const operatorInput = screen.getByLabelText('Operator ID');
    await user.clear(operatorInput);
    await user.type(operatorInput, 'ops-ui-qa');
    await user.click(screen.getByRole('button', { name: 'Save' }));

    const stored = JSON.parse(localStorage.getItem(SETTINGS_KEY) ?? '{}') as Partial<PanelSettings>;
    expect(stored.operatorId).toBe('ops-ui-qa');
    expect(await screen.findByText('Settings saved')).toBeInTheDocument();
  });
});
