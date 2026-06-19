import type { EnterpriseWorkspaceSnapshot } from './enterpriseWorkspaceTypes';

export type EnterpriseWorkspaceViewModel = {
  status: EnterpriseWorkspaceSnapshot['status'];
  organizationName: string;
  workspaceCount: number;
  principalCount: number;
  membershipCount: number;
  activeAgentCount: number;
  pendingApprovalCount: number;
  deviceCount: number;
  identityStatus: string;
  networkListenerLabel: string;
  rawSecretsExposed: false;
  blockingReasons: string[];
};

export function mapEnterpriseWorkspace(snapshot?: EnterpriseWorkspaceSnapshot | null): EnterpriseWorkspaceViewModel {
  const safe = snapshot ?? disabledEnterpriseWorkspaceSnapshot();
  return {
    status: safe.status,
    organizationName: safe.organization?.displayName ?? 'setup required',
    workspaceCount: safe.workspaces.length,
    principalCount: safe.principals.length,
    membershipCount: safe.memberships.length,
    activeAgentCount: safe.enrollments.active,
    pendingApprovalCount: safe.enrollments.pendingApproval,
    deviceCount: safe.devices.length,
    identityStatus: safe.identity.verified ? 'verified' : safe.identity.errorCode ?? 'unverified',
    networkListenerLabel: safe.networkListenerEnabled ? 'enabled' : 'disabled',
    rawSecretsExposed: false,
    blockingReasons: safe.blockingReasons,
  };
}

export function disabledEnterpriseWorkspaceSnapshot(): EnterpriseWorkspaceSnapshot {
  return {
    schemaVersion: 'enterprise-workspace-snapshot/v1',
    status: 'disabled',
    identity: { enabled: false, verified: false, errorCode: 'IDENTITY_DISABLED' },
    organization: null,
    workspaces: [],
    currentWorkspaceId: null,
    principals: [],
    memberships: [],
    roles: [],
    devices: [],
    enrollments: { active: 0, pendingApproval: 0, revoked: 0, expiredTokens: 0 },
    permissionMatrix: {},
    blockingReasons: [],
    rawSecretsExposed: false,
    networkListenerEnabled: false,
    generatedAtUtc: new Date(0).toISOString(),
  };
}
