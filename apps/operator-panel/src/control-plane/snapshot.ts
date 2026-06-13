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
    pilotLaunch: {
      schemaVersion: 'control-plane.pilot-launch-readiness/v1',
      generatedAtUtc: new Date(0).toISOString(),
      status: 'blocked',
      headline: 'Pilot launch candidate is blocked.',
      artifactRoot: 'artifacts/design-partner-pilot',
      enterpriseHatA: missingPilotTile('enterprise-hat-a', 'Enterprise Hat A'),
      installRehearsal: missingPilotTile('install-rehearsal', 'Install rehearsal'),
      externalAgentPilot: missingPilotTile('external-agent-pilot', 'External agent pilot'),
      governanceAdmin: missingPilotTile('governance-admin', 'Governance admin'),
      securityReview: missingPilotTile('security-review', 'Security review'),
      claimGuard: {
        tileId: 'claim-guard',
        label: 'Claim guard',
        status: 'blocked',
        detail: 'snapshot unavailable',
        path: null,
        blockingReasons: ['SNAPSHOT_UNAVAILABLE'],
      },
      evidenceCorpus: missingPilotTile('evidence-corpus', 'Evidence corpus'),
      pilotMetrics: missingPilotTile('pilot-metrics', 'Pilot metrics'),
      adminProposals: [],
      nextActions: [{ label: 'SNAPSHOT_UNAVAILABLE', severity: 'blocking', target: 'System' }],
      blockers: ['SNAPSHOT_UNAVAILABLE'],
      warnings: [],
    },
    codeIntelligence: missingCodeIntelligence(),
    pilotOperations: missingPilotOperations(),
    designPartnerBeta: missingDesignPartnerBeta(),
    providerGovernance: {
      contractVersion: 'control-plane.provider-governance/v1',
      generatedAtUtc: new Date(0).toISOString(),
      providers: [],
      overallStatus: 'blocked',
      blockingReasons: ['SNAPSHOT_UNAVAILABLE'],
    },
    providerRuntime: {
      contractVersion: 'control-plane.provider-runtime/v1',
      generatedAtUtc: new Date(0).toISOString(),
      enabled: false,
      latestInvocations: [],
      workflowProofs: [],
      blockingReasons: ['SNAPSHOT_UNAVAILABLE'],
    },
    targetEvidenceClosure: {
      contractVersion: 'control-plane.target-evidence-closure/v1',
      generatedAtUtc: new Date(0).toISOString(),
      status: 'unknown',
      sessionId: null,
      mode: null,
      evidenceMode: null,
      rawPersistence: false,
      blockingReasons: ['SNAPSHOT_UNAVAILABLE'],
      warnings: [],
      blockedClaims: [],
      attestationStatus: 'missing',
    },
    quickActions: [],
    partialReasons: [],
  };
}

function missingPilotTile(tileId: string, label: string) {
  return {
    tileId,
    label,
    status: 'missing' as const,
    detail: 'snapshot unavailable',
    path: null,
    blockingReasons: ['SNAPSHOT_UNAVAILABLE'],
  };
}

function missingCodeIntelligence() {
  return {
    schemaVersion: 'control-plane.code-intelligence-summary/v1' as const,
    generatedAtUtc: new Date(0).toISOString(),
    status: 'missing' as const,
    verdict: 'missing',
    tool: 'fallow',
    toolVersion: null,
    artifactRoot: 'artifacts/code-intelligence/fallow',
    telemetryDisabled: true,
    boundaryViolations: 0,
    secretScanStatus: 'unknown',
    buckets: [],
    blockers: ['SNAPSHOT_UNAVAILABLE'],
    warnings: [],
  };
}

function missingPilotOperations() {
  return {
    schemaVersion: 'control-plane.pilot-operations/v1' as const,
    generatedAtUtc: new Date(0).toISOString(),
    status: 'blocked' as const,
    headline: 'Pilot operations are blocked.',
    artifactRoot: 'artifacts/pilot-ops',
    checklist: [
      {
        itemId: 'snapshot-load',
        label: 'Snapshot load',
        status: 'blocked' as const,
        detail: 'snapshot unavailable',
        path: null,
        blocking: true,
      },
    ],
    timeline: [],
    acceptanceMetrics: {},
    feedbackBundlePath: null,
    nextActions: [{ label: 'SNAPSHOT_UNAVAILABLE', severity: 'blocking' as const, target: 'System' }],
    blockers: ['SNAPSHOT_UNAVAILABLE'],
    warnings: [],
  };
}

function missingDesignPartnerBeta() {
  return {
    schemaVersion: 'control-plane.design-partner-beta/v1' as const,
    generatedAtUtc: new Date(0).toISOString(),
    status: 'blocked' as const,
    headline: 'Design Partner Beta Operations Candidate is blocked.',
    artifactRoot: 'artifacts/design-partner-beta',
    codeIntelligence: missingCodeIntelligence(),
    pilotOperations: missingPilotOperations(),
    checks: [
      {
        itemId: 'snapshot-load',
        label: 'Snapshot load',
        status: 'blocked' as const,
        detail: 'snapshot unavailable',
        path: null,
        blocking: true,
      },
    ],
    blockers: ['SNAPSHOT_UNAVAILABLE'],
    warnings: [],
  };
}
