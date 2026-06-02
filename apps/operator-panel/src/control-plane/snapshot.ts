import { assertNoSilentMockFallback } from './dataSource';
import type { ControlPlaneSnapshot, PageViewModel } from './types';

export interface ControlPlaneBridge {
  getControlPlaneSnapshot(options?: { forceRefresh?: boolean }): Promise<ControlPlaneSnapshot>;
}

let cachedSnapshot: ControlPlaneSnapshot | null = null;

export function clearControlPlaneSnapshotCache(): void {
  cachedSnapshot = null;
}

export async function loadControlPlaneSnapshot(
  bridge: ControlPlaneBridge,
  options: { forceRefresh?: boolean } = {},
): Promise<PageViewModel<ControlPlaneSnapshot>> {
  try {
    if (!cachedSnapshot || options.forceRefresh) {
      cachedSnapshot = await bridge.getControlPlaneSnapshot({ forceRefresh: options.forceRefresh });
    }
    assertNoSilentMockFallback(cachedSnapshot.dataSource);
    return {
      pageId: 'control-plane-snapshot',
      title: 'Control Plane Snapshot',
      subtitle: cachedSnapshot.system.health.humanSummary,
      dataSource: cachedSnapshot.dataSource,
      loading: false,
      data: cachedSnapshot,
      empty: isSnapshotEmpty(cachedSnapshot)
        ? {
            title: 'No control-plane activity',
            detail: 'Register an agent or submit a governed run to populate the live snapshot.',
          }
        : undefined,
      debug: {
        generatedAtUtc: cachedSnapshot.generatedAtUtc,
        partialReasons: cachedSnapshot.partialReasons,
      },
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Snapshot load failed.';
    return {
      pageId: 'control-plane-snapshot',
      title: 'Control Plane Snapshot',
      dataSource: {
        mode: 'error',
        isMock: false,
        isSilentFallback: false,
        lastRefreshUtc: null,
        ageMs: null,
        freshness: 'unknown',
        contractVersion: 'control-plane.snapshot/v1',
        sourceReason: message,
      },
      loading: false,
      error: {
        code: error instanceof Error ? error.name : 'SNAPSHOT_LOAD_FAILED',
        message,
      },
      data: emptySnapshot(),
    };
  }
}

function isSnapshotEmpty(snapshot: ControlPlaneSnapshot): boolean {
  return snapshot.agents.length === 0 && snapshot.runs.length === 0 && snapshot.approvals.length === 0;
}

function emptySnapshot(): ControlPlaneSnapshot {
  return {
    contractVersion: 'control-plane.snapshot/v1',
    generatedAtUtc: new Date(0).toISOString(),
    dataSource: {
      mode: 'error',
      isMock: false,
      isSilentFallback: false,
      lastRefreshUtc: null,
      ageMs: null,
      freshness: 'unknown',
      contractVersion: 'control-plane.snapshot/v1',
      sourceReason: 'snapshot unavailable',
    },
    system: {
      profile: 'unknown',
      rootDir: '',
      coreVersion: '',
      contractVersion: '',
      health: {
        status: 'unknown',
        confidence: 'low',
        missingSignals: [],
        blockingReasons: [],
        lastDoctorStatus: 'unknown',
        humanSummary: 'Snapshot unavailable.',
      },
      doctor: {},
      capabilities: {},
      configSummary: {},
      sourceMap: {},
      warnings: [],
    },
    dashboard: {
      agentCount: 0,
      runCount: 0,
      pendingApprovalCount: 0,
      evidencePackCount: 0,
      activeAlertCount: 0,
      blockedClaimCount: 0,
      conditionalClaimCount: 0,
    },
    agents: [],
    runs: [],
    approvals: [],
    evidencePacks: [],
    policyPacks: [],
    executionSurfaces: [],
    logs: [],
    alerts: [],
    reports: [],
    operations: [],
    admin: {
      users: [],
      roles: [],
      policyPacks: [],
      permissionMatrix: {},
      source: 'local_fixture',
    },
    designPartnerRc: {
      schemaVersion: 'control-plane.design-partner-rc/v1',
      generatedAtUtc: new Date(0).toISOString(),
      status: 'blocked',
      checks: [
        {
          checkId: 'snapshot-load',
          label: 'Snapshot load',
          status: 'failed',
          detail: 'snapshot unavailable',
          blocking: true,
        },
      ],
      blockers: ['snapshot-load'],
      warnings: [],
      artifactRoot: 'artifacts/design-partner-rc',
    },
    quickActions: [],
    partialReasons: [],
  };
}
