import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';

import { EnterpriseWorkspaceOverview } from './EnterpriseWorkspaceOverview';
import type { EnterpriseWorkspaceSnapshot } from './enterpriseWorkspaceTypes';

test('renders enterprise workspace summary without raw secrets', () => {
  render(<EnterpriseWorkspaceOverview snapshot={snapshot} locale="en" />);

  expect(screen.getByTestId('enterprise-workspace')).toBeInTheDocument();
  expect(screen.getByText('Local Org')).toBeInTheDocument();
  expect(screen.getByText('disabled')).toBeInTheDocument();
  expect(screen.queryByText(/rawToken/i)).not.toBeInTheDocument();
});

const snapshot: EnterpriseWorkspaceSnapshot = {
  schemaVersion: 'enterprise-workspace-snapshot/v1',
  status: 'ready',
  identity: { enabled: true, verified: true, actorId: 'preview-operator' },
  organization: { organizationId: 'local-org', displayName: 'Local Org', status: 'active' },
  workspaces: [{ workspaceId: 'pilot-workspace', displayName: 'Pilot Workspace', status: 'active', environment: 'pilot' }],
  currentWorkspaceId: 'pilot-workspace',
  principals: [{ principalId: 'preview-operator', displayName: 'Preview Operator', status: 'active' }],
  memberships: [{ membershipId: 'member-preview', principalId: 'preview-operator', workspaceId: 'pilot-workspace', roles: ['platform_admin'], status: 'active' }],
  roles: [],
  devices: [{ deviceId: 'device-host-01', status: 'active', workspaceId: 'pilot-workspace' }],
  enrollments: { active: 1, pendingApproval: 0, revoked: 0, expiredTokens: 0 },
  permissionMatrix: {},
  blockingReasons: [],
  rawSecretsExposed: false,
  networkListenerEnabled: false,
  generatedAtUtc: '2026-06-19T00:00:00Z',
};
