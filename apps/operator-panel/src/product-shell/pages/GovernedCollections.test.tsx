import { act, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

const artifacts = vi.hoisted(() => ({ list: vi.fn(), get: vi.fn() }));
const bridge = vi.hoisted(() => ({
  listControlPlaneAgents: vi.fn(),
  fetchApprovals: vi.fn(),
  showApproval: vi.fn(),
  decideApproval: vi.fn(),
}));

vi.mock('../../artifact-workspace/artifactBridge', () => ({ artifactBridge: artifacts }));
vi.mock('../../bridge', () => bridge);

import { renderOperatorPanel } from '../../test/render';
import { AgentsPage, ApprovalsPage, LibraryPage } from './GovernedCollections';

describe('LibraryPage', () => {
  it('ignores old artifact detail after another artifact is selected', async () => {
    artifacts.list.mockResolvedValue({ items: [
      { artifactId: 'artifact-old', title: 'Old artifact', kind: 'document', status: 'active' },
      { artifactId: 'artifact-new', title: 'New artifact', kind: 'document', status: 'active' },
    ] });
    let finishOld!: (value: unknown) => void;
    artifacts.get.mockImplementation(({ artifactId }) => artifactId === 'artifact-old'
      ? new Promise((resolve) => { finishOld = resolve; })
      : Promise.resolve({ revision: { revisionId: 'revision-new' } }));
    const { user } = renderOperatorPanel(<MemoryRouter><LibraryPage /></MemoryRouter>);
    await waitFor(() => expect(finishOld).toBeDefined());
    await user.click(await screen.findByRole('button', { name: /New artifact/ }));
    expect(await screen.findByText('revision-new')).toBeInTheDocument();
    await act(async () => { finishOld({ revision: { revisionId: 'revision-old' } }); });
    expect(screen.queryByText('revision-old')).not.toBeInTheDocument();
    expect(screen.getByText('revision-new')).toBeInTheDocument();
  });

  it('ignores old approval evidence after the selected approval changes', async () => {
    bridge.fetchApprovals.mockResolvedValue({ pending: [
      { approval_id: 'approval-old', target_kind: 'deployment', status: 'pending' },
      { approval_id: 'approval-new', target_kind: 'deployment', status: 'pending' },
    ] });
    let finishOld!: (value: unknown) => void;
    bridge.showApproval.mockImplementation((_settings, id) => id === 'approval-old'
      ? new Promise((resolve) => { finishOld = resolve; })
      : Promise.resolve({ ticket: { target_ref: 'new-target' } }));
    const { user } = renderOperatorPanel(<MemoryRouter><ApprovalsPage /></MemoryRouter>);
    await waitFor(() => expect(finishOld).toBeDefined());
    await user.click(await screen.findByRole('button', { name: /approval-new/ }));
    expect(await screen.findByText('new-target')).toBeInTheDocument();
    await act(async () => { finishOld({ ticket: { target_ref: 'old-target' } }); });
    expect(screen.queryByText('old-target')).not.toBeInTheDocument();
    expect(screen.getByText('new-target')).toBeInTheDocument();
  });

  it('opens the canonical detail for a selected governed artifact', async () => {
    artifacts.list.mockResolvedValue({
      items: [{ artifactId: 'artifact-release', title: 'Release plan', kind: 'document', status: 'active' }],
    });
    artifacts.get.mockResolvedValue({ artifact: { artifactId: 'artifact-release', title: 'Release plan' }, revision: { revisionId: 'revision-1' } });

    const { container } = renderOperatorPanel(<MemoryRouter><LibraryPage /></MemoryRouter>);

    expect(container.querySelector('.collection-page .collection-list')).toBeInTheDocument();
    expect(container.querySelector('.collection-icon')).toBeInTheDocument();
    expect(container.querySelector('.collection-detail-panel')).toBeInTheDocument();
    await screen.findByRole('button', { name: /Release plan/ });
    await waitFor(() => expect(artifacts.get).toHaveBeenCalledWith({ artifactId: 'artifact-release' }));
    expect(await screen.findByText(/revision-1/)).toBeInTheDocument();
    expect(container.querySelector('pre')).not.toBeInTheDocument();
  });

  it('renders approval evidence as labeled fields rather than primary raw JSON', async () => {
    bridge.fetchApprovals.mockResolvedValue({
      pending: [{ approval_id: 'approval-release', target_kind: 'deployment', status: 'pending' }],
    });
    bridge.showApproval.mockResolvedValue({
      approval_id: 'approval-release',
      status: 'pending',
      execution_status: 'not_executed',
      ticket: {
        run_id: 'run-release',
        target_kind: 'deployment',
        target_ref: 'production',
        expires_at: '2026-07-30T12:00:00Z',
        actor: 'policy-router',
        decision_reason: 'POLICY_REQUIRE_APPROVAL',
        snapshot: { risk_class: 'high', category: 'external_action' },
      },
    });

    const { container } = renderOperatorPanel(<MemoryRouter><ApprovalsPage /></MemoryRouter>);

    expect(await screen.findByText('run-release')).toBeInTheDocument();
    expect(screen.getByText('high')).toBeInTheDocument();
    expect(container.querySelector('pre')).not.toBeInTheDocument();
  });

  it('opens the requested governed agent detail from a canonical search route', async () => {
    bridge.listControlPlaneAgents.mockResolvedValue({ agents: [{
      agent_id: 'release-agent', display_name: 'Release Agent', runtime_kind: 'imperaos_team',
      agent_type: 'internal', status: 'active', readiness: 'ready', policy_pack_id: 'release-policy',
      risk_profile: 'guarded', last_evidence_status: 'valid',
    }] });

    const { container } = renderOperatorPanel(<MemoryRouter initialEntries={['/agents?agent=release-agent']}><AgentsPage /></MemoryRouter>);

    expect(container.querySelector('.collection-page.agents-collection-page')).toBeInTheDocument();
    const agent = await screen.findByRole('button', { name: /Release Agent/ });
    expect(agent).toHaveAttribute('aria-pressed', 'true');
    expect(await screen.findByText('release-policy')).toBeInTheDocument();
  });
});
