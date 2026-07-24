import { screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

const artifacts = vi.hoisted(() => ({ list: vi.fn(), get: vi.fn() }));
const bridge = vi.hoisted(() => ({ listControlPlaneAgents: vi.fn() }));

vi.mock('../../artifact-workspace/artifactBridge', () => ({ artifactBridge: artifacts }));
vi.mock('../../bridge', () => bridge);

import { renderOperatorPanel } from '../../test/render';
import { AgentsPage, LibraryPage } from './GovernedCollections';

describe('LibraryPage', () => {
  it('opens the canonical detail for a selected governed artifact', async () => {
    artifacts.list.mockResolvedValue({
      items: [{ artifactId: 'artifact-release', title: 'Release plan', kind: 'document', status: 'active' }],
    });
    artifacts.get.mockResolvedValue({ artifact: { artifactId: 'artifact-release', title: 'Release plan' }, revision: { revisionId: 'revision-1' } });

    renderOperatorPanel(<MemoryRouter><LibraryPage /></MemoryRouter>);

    await screen.findByRole('button', { name: /Release plan/ });
    await waitFor(() => expect(artifacts.get).toHaveBeenCalledWith({ artifactId: 'artifact-release' }));
    expect(await screen.findByText(/revision-1/)).toBeInTheDocument();
  });

  it('opens the requested governed agent detail from a canonical search route', async () => {
    bridge.listControlPlaneAgents.mockResolvedValue({ agents: [{
      agent_id: 'release-agent', display_name: 'Release Agent', runtime_kind: 'imperaos_team',
      agent_type: 'internal', status: 'active', readiness: 'ready', policy_pack_id: 'release-policy',
      risk_profile: 'guarded', last_evidence_status: 'valid',
    }] });

    renderOperatorPanel(<MemoryRouter initialEntries={['/agents?agent=release-agent']}><AgentsPage /></MemoryRouter>);

    const agent = await screen.findByRole('button', { name: /Release Agent/ });
    expect(agent).toHaveAttribute('aria-pressed', 'true');
    expect(await screen.findByText('release-policy')).toBeInTheDocument();
  });
});
