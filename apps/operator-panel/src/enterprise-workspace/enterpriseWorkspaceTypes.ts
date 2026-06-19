export type EnterpriseWorkspaceStatus = 'ready' | 'setup_required' | 'blocked' | 'disabled';

export interface EnterpriseIdentitySummary {
  enabled: boolean;
  verified: boolean;
  actorId?: string | null;
  errorCode?: string | null;
}

export interface EnterpriseOrganizationSummary {
  organizationId: string;
  displayName: string;
  status: string;
}

export interface EnterpriseWorkspaceSummary {
  workspaceId: string;
  displayName: string;
  status: string;
  environment?: string | null;
}

export interface EnterprisePrincipalSummary {
  principalId: string;
  displayName: string;
  principalType?: string | null;
  status: string;
}

export interface EnterpriseMembershipSummary {
  membershipId: string;
  principalId?: string | null;
  workspaceId?: string | null;
  roles: string[];
  status: string;
}

export interface CanonicalRoleSummary {
  roleId: string;
  label: string;
  risk: string;
  permissions: string[];
}

export interface EnterpriseDeviceSummary {
  deviceId: string;
  status: string;
  workspaceId?: string | null;
  principalId?: string | null;
  displayName?: string | null;
  platform?: string | null;
}

export interface EnterpriseEnrollmentSummary {
  active: number;
  pendingApproval: number;
  revoked: number;
  expiredTokens: number;
}

export interface EnterpriseWorkspaceSnapshot {
  schemaVersion: 'enterprise-workspace-snapshot/v1';
  status: EnterpriseWorkspaceStatus;
  identity: EnterpriseIdentitySummary;
  organization: EnterpriseOrganizationSummary | null;
  workspaces: EnterpriseWorkspaceSummary[];
  currentWorkspaceId: string | null;
  principals: EnterprisePrincipalSummary[];
  memberships: EnterpriseMembershipSummary[];
  roles: CanonicalRoleSummary[];
  devices: EnterpriseDeviceSummary[];
  enrollments: EnterpriseEnrollmentSummary;
  permissionMatrix: Record<string, string[]>;
  blockingReasons: string[];
  rawSecretsExposed: false;
  networkListenerEnabled: false;
  generatedAtUtc: string;
}
