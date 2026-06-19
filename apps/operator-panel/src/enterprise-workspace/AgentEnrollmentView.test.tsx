import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';

import { AgentEnrollmentView } from './AgentEnrollmentView';

test('renders enrollment counts and shown-once warning', () => {
  render(
    <AgentEnrollmentView
      snapshot={{
        schemaVersion: 'enterprise-workspace-snapshot/v1',
        status: 'ready',
        identity: { enabled: true, verified: true },
        organization: null,
        workspaces: [],
        currentWorkspaceId: null,
        principals: [],
        memberships: [],
        roles: [],
        devices: [],
        enrollments: { active: 2, pendingApproval: 1, revoked: 0, expiredTokens: 0 },
        permissionMatrix: {},
        blockingReasons: [],
        rawSecretsExposed: false,
        networkListenerEnabled: false,
        generatedAtUtc: '2026-06-19T00:00:00Z',
      }}
      locale="en"
    />,
  );

  expect(screen.getByRole('alert')).toHaveTextContent('shown once only');
  expect(screen.queryByText(/shown-once-token-test-value/i)).not.toBeInTheDocument();
});
