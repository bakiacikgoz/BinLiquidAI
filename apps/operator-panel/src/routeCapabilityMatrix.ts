import type { RouteId } from './routeRegistry';
import { routes } from './routeRegistry';

export type RouteActionState = 'working' | 'disabled_with_reason' | 'preview_only';

export type RouteCapability = {
  routeId: RouteId;
  title: string;
  dataSource: 'bridge' | 'snapshot' | 'preview_only';
  primaryActions: Array<{
    actionId: string;
    label: string;
    state: RouteActionState;
    bridgeCommand?: string;
    cliCommand?: string;
    requiredPermission?: string;
    disabledReasonCode?: string;
    noShipIfInert: boolean;
  }>;
};

const bridgeActions: Partial<Record<RouteId, RouteCapability['primaryActions']>> = {
  assistant: [
    {
      actionId: 'assistant.start_turn',
      label: 'Send',
      state: 'working',
      bridgeCommand: 'bridge_assistant_start_turn',
      requiredPermission: 'runtime.run',
      noShipIfInert: true,
    },
    {
      actionId: 'assistant.cancel_turn',
      label: 'Stop',
      state: 'working',
      bridgeCommand: 'bridge_assistant_cancel_turn',
      requiredPermission: 'runtime.run',
      noShipIfInert: true,
    },
  ],
  agents: [
    {
      actionId: 'agent.register',
      label: 'Register agent',
      state: 'working',
      bridgeCommand: 'bridge_control_plane_agent_register',
      cliCommand: 'binliquid control-plane agent register',
      requiredPermission: 'agent.registry.write',
      noShipIfInert: true,
    },
  ],
  runs: [
    {
      actionId: 'run.submit',
      label: 'Submit run',
      state: 'working',
      bridgeCommand: 'bridge_control_plane_run_submit',
      cliCommand: 'binliquid control-plane run submit',
      requiredPermission: 'runtime.run',
      noShipIfInert: true,
    },
  ],
  approvals: [
    {
      actionId: 'approval.decide',
      label: 'Approve',
      state: 'working',
      bridgeCommand: 'bridge_approval_decide',
      cliCommand: 'binliquid approval decide',
      requiredPermission: 'approval.decide',
      noShipIfInert: true,
    },
  ],
  evidence: [
    {
      actionId: 'evidence.verify_latest',
      label: 'Verify latest',
      state: 'working',
      bridgeCommand: 'bridge_evidence_verify',
      cliCommand: 'binliquid control-plane evidence verify',
      requiredPermission: 'evidence.verify',
      noShipIfInert: true,
    },
  ],
  'enterprise-workspace': [
    {
      actionId: 'workspace.bootstrap',
      label: 'Bootstrap workspace',
      state: 'working',
      bridgeCommand: 'bridge_enterprise_workspace_bootstrap',
      cliCommand: 'binliquid enterprise workspace bootstrap',
      requiredPermission: 'workspace.bootstrap',
      noShipIfInert: true,
    },
  ],
  'enterprise-enrollment': [
    {
      actionId: 'enrollment.token_create',
      label: 'Create token',
      state: 'working',
      bridgeCommand: 'bridge_enterprise_enrollment_token_create',
      cliCommand: 'binliquid enterprise enrollment token create',
      requiredPermission: 'agent.enrollment.create',
      noShipIfInert: true,
    },
  ],
  'memory-authority': [
    {
      actionId: 'memory.query',
      label: 'Query memory',
      state: 'working',
      bridgeCommand: 'bridge_memory_workspace_query',
      cliCommand: 'binliquid memory workspace authority query',
      requiredPermission: 'memory.read',
      noShipIfInert: true,
    },
  ],
  'governed-pilot-workflow': [
    {
      actionId: 'workflow.run',
      label: 'Run workflow',
      state: 'working',
      bridgeCommand: 'bridge_governed_pilot_workflow_run',
      cliCommand: 'binliquid pilot workflow run',
      requiredPermission: 'runtime.run',
      noShipIfInert: true,
    },
  ],
  surfaces: [
    {
      actionId: 'computer_use.live_execute',
      label: 'Live execute',
      state: 'disabled_with_reason',
      disabledReasonCode: 'COMPUTER_USE_NOT_QUALIFIED',
      requiredPermission: 'computer_use.execute',
      noShipIfInert: true,
    },
  ],
  settings: [
    {
      actionId: 'settings.bridge_handshake',
      label: 'Bridge handshake',
      state: 'working',
      bridgeCommand: 'bridge_system_snapshot',
      cliCommand: 'binliquid operator snapshot',
      noShipIfInert: true,
    },
  ],
};

const snapshotOnlyRoutes = new Set<RouteId>([
  'dashboard',
  'workspace',
  'tasks',
  'system',
  'enterprise-users',
  'enterprise-roles',
  'enterprise-fleet',
  'enterprise-identity',
  'memory-governance',
  'memory-runtime',
  'memory-semantic',
  'policy',
  'operations',
  'logs',
  'reports',
  'alerts',
  'plans',
  'users',
  'roles',
  'policy-packs',
  'design-partner-field-evidence',
  'design-partner-handoff',
  'mainline-rc-freeze',
  'rc-gate-evidence',
  'rc-release-decision',
]);

export const routeCapabilityMatrix: RouteCapability[] = routes.map((route) => ({
  routeId: route.routeId,
  title: route.heading,
  dataSource: snapshotOnlyRoutes.has(route.routeId) ? 'snapshot' : 'bridge',
  primaryActions: bridgeActions[route.routeId] ?? [],
}));
