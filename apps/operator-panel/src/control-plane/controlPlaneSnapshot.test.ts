import { beforeEach, describe, expect, it } from 'vitest';

import { assertNoSilentMockFallback, describeDataSource, SilentMockFallbackError } from './dataSource';
import { clearControlPlaneSnapshotCache, loadControlPlaneSnapshot } from './snapshot';
import type { ControlPlaneSnapshot } from './types';

describe('controlPlaneSnapshot runtime truth', () => {
  beforeEach(() => {
    clearControlPlaneSnapshotCache();
  });

  it('loads a live snapshot into a page view model', async () => {
    const snapshot = makeSnapshot();
    const vm = await loadControlPlaneSnapshot({
      getControlPlaneSnapshot: async () => snapshot,
    });

    expect(vm.error).toBeUndefined();
    expect(vm.data.contractVersion).toBe('control-plane.snapshot/v1');
    expect(vm.dataSource.mode).toBe('cli_live');
    expect(vm.subtitle).toBe('Partial pilot readiness.');
    expect(vm.empty).toBeUndefined();
  });

  it('fails closed when live mode silently falls back to mock data', async () => {
    const snapshot = makeSnapshot({
      dataSource: {
        ...makeSnapshot().dataSource,
        mode: 'preview_fixture',
        isMock: true,
        isSilentFallback: true,
      },
    });

    expect(() => assertNoSilentMockFallback(snapshot.dataSource)).toThrow(SilentMockFallbackError);
    const vm = await loadControlPlaneSnapshot({
      getControlPlaneSnapshot: async () => snapshot,
    });

    expect(vm.error?.code).toBe('SilentMockFallbackError');
    expect(vm.dataSource.mode).toBe('error');
    expect(describeDataSource(snapshot.dataSource)).toContain('fail closed');
  });

  it('reuses cached snapshots until force refresh is requested', async () => {
    let calls = 0;
    const bridge = {
      getControlPlaneSnapshot: async () => {
        calls += 1;
        return makeSnapshot({
          dashboard: {
            ...makeSnapshot().dashboard,
            runCount: calls,
          },
        });
      },
    };

    const first = await loadControlPlaneSnapshot(bridge);
    const cached = await loadControlPlaneSnapshot(bridge);
    const refreshed = await loadControlPlaneSnapshot(bridge, { forceRefresh: true });

    expect(first.data.dashboard.runCount).toBe(1);
    expect(cached.data.dashboard.runCount).toBe(1);
    expect(refreshed.data.dashboard.runCount).toBe(2);
  });
});

function makeSnapshot(overrides: Partial<ControlPlaneSnapshot> = {}): ControlPlaneSnapshot {
  const generatedAtUtc = '2026-06-01T12:00:00.000Z';
  return {
    contractVersion: 'control-plane.snapshot/v1',
    generatedAtUtc,
    dataSource: {
      mode: 'cli_live',
      isMock: false,
      isSilentFallback: false,
      lastRefreshUtc: generatedAtUtc,
      ageMs: 0,
      freshness: 'fresh',
      contractVersion: 'control-plane.snapshot/v1',
      sourceReason: 'CLI generated live snapshot',
    },
    system: {
      profile: 'lite',
      rootDir: '.binliquid/control-plane',
      coreVersion: '0.5.0',
      contractVersion: '2.0',
      health: {
        status: 'partial',
        confidence: 'medium',
        missingSignals: ['metrics_snapshot'],
        blockingReasons: [],
        lastDoctorStatus: 'healthy',
        humanSummary: 'Partial pilot readiness.',
      },
      doctor: { status: 'healthy' },
      capabilities: { controlPlaneSnapshot: true },
      configSummary: { governanceEnabled: true },
      sourceMap: { runs: 'control-plane run store' },
      warnings: ['metrics_snapshot'],
    },
    dashboard: {
      agentCount: 1,
      runCount: 1,
      pendingApprovalCount: 1,
      evidencePackCount: 0,
      activeAlertCount: 1,
      blockedClaimCount: 3,
      conditionalClaimCount: 1,
    },
    agents: [
      {
        agentId: 'governed-ops',
        displayName: 'Governed Ops',
        runtimeKind: 'binliquid_team',
        status: 'registered',
        readiness: 'policy_simulated',
        ownerTeam: 'platform',
        lastRunId: 'cp-run-preview',
        lastEvidencePackId: null,
      },
    ],
    runs: [
      {
        runId: 'cp-run-preview',
        agentId: 'governed-ops',
        profile: 'lite',
        status: 'approval_pending',
        submittedBy: 'cli:operator',
        identityRef: 'identity:disabled',
        inputHash: 'sha256:input',
        policyHash: 'sha256:policy',
        startedAt: generatedAtUtc,
        completedAt: null,
        approvalIds: ['approval-preview'],
        artifactRefs: [],
        evidencePackId: null,
        blockingReasons: [],
        nextActions: ['approval.show'],
      },
    ],
    approvals: [
      {
        approvalId: 'approval-preview',
        runId: 'cp-run-preview',
        status: 'pending',
        targetKind: 'control_plane_action',
        targetRef: 'governed-ops:inspect_queue',
        actionHash: 'sha256:action',
        policyHash: 'sha256:policy',
        requestHash: 'sha256:request',
        snapshotHash: 'sha256:snapshot',
        executionStatus: 'not_executed',
        createdAt: generatedAtUtc,
        expiresAt: '2026-06-02T12:00:00.000Z',
        actor: null,
        disabledReason: null,
      },
    ],
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
      generatedAtUtc,
      status: 'conditional',
      checks: [],
      blockers: [],
      warnings: ['evidence-index'],
      artifactRoot: 'artifacts/design-partner-rc',
    },
    quickActions: [],
    partialReasons: ['metrics_snapshot'],
    ...overrides,
  };
}
