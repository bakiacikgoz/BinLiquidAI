import type { RouteCapability } from './routeCapabilityMatrix';

export type BridgeCommandParityIssue = {
  routeId: string;
  actionId: string;
  reason: string;
};

export function registeredBridgeCommands(libSource: string): Set<string> {
  return new Set(
    Array.from(libSource.matchAll(/bridge::(bridge_[A-Za-z0-9_]+)/g), (match) => match[1]),
  );
}

export function assertRouteBridgeCommandParity(
  matrix: RouteCapability[],
  libSource: string,
): {
  status: 'passed';
  checkedActions: number;
  registeredCommands: number;
} {
  const registered = registeredBridgeCommands(libSource);
  const issues: BridgeCommandParityIssue[] = [];
  let checkedActions = 0;

  for (const route of matrix) {
    for (const action of route.primaryActions) {
      checkedActions += 1;
      if (action.state === 'working' && action.bridgeCommand && !registered.has(action.bridgeCommand)) {
        issues.push({
          routeId: route.routeId,
          actionId: action.actionId,
          reason: `missing registered Tauri handler ${action.bridgeCommand}`,
        });
      }
      if (action.state === 'working' && !action.bridgeCommand && !action.cliCommand) {
        issues.push({
          routeId: route.routeId,
          actionId: action.actionId,
          reason: 'working action has no bridgeCommand or cliCommand',
        });
      }
      if (action.state === 'disabled_with_reason' && !/^[A-Z0-9_]+$/.test(action.disabledReasonCode ?? '')) {
        issues.push({
          routeId: route.routeId,
          actionId: action.actionId,
          reason: 'disabled action is missing an uppercase disabledReasonCode',
        });
      }
    }
  }

  if (issues.length > 0) {
    throw new Error(
      [
        'Bridge command parity failed:',
        ...issues.map((issue) => `- ${issue.routeId}/${issue.actionId}: ${issue.reason}`),
      ].join('\n'),
    );
  }

  return {
    status: 'passed',
    checkedActions,
    registeredCommands: registered.size,
  };
}
