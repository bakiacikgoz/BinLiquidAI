import { describe, expect, it } from 'vitest';

import {
  buildActivityItems,
  buildNotificationItems,
  buildPendingApprovalSummaries,
  buildRuntimeSummaryItems,
  buildSystemHealthSummary,
  mapWorkspaceStageToMissionStage,
} from './missionMappers';
import type { WorkspaceSnapshot } from './workspace';

const clock = (value: string, fallback: string) => (value ? '09:31:00' : fallback);

const baseSnapshot: WorkspaceSnapshot = {
  objective: 'Inspect queue',
  stage: 'planning',
  progressIndex: 0,
  progressTotal: 5,
  currentStatus: 'running',
  blockedReason: null,
  liveSurface: null,
  runtimeState: {
    displayState: 'running',
    rawState: 'running',
    registryState: null,
    activeSession: true,
    recoveryState: null,
    recoverySummary: null,
    controlHistoryCount: 0,
    pendingApprovalId: null,
    pendingCommand: null,
    lastSafeCheckpoint: null,
    lastControlCommand: null,
    lastControlOutcome: null,
    lastControlReason: null,
    resumeAllowed: false,
    stoppedByUser: false,
    lastVerificationSummary: null,
    canPause: true,
    canResume: false,
    canStop: true,
  },
  transcript: [],
  timeline: [],
  artifacts: [],
};

describe('mission mappers', () => {
  it('maps pending approvals into approval stage regardless of workspace stage', () => {
    expect(mapWorkspaceStageToMissionStage('planning', true)).toBe('approval');
    expect(mapWorkspaceStageToMissionStage('reading_screen')).toBe('preparing');
    expect(mapWorkspaceStageToMissionStage('executing')).toBe('running');
    expect(mapWorkspaceStageToMissionStage('done')).toBe('done');
  });

  it('does not invent live activity rows when no timeline exists', () => {
    const items = buildActivityItems(baseSnapshot, clock);

    expect(items).toHaveLength(1);
    expect(items[0]?.time).toBe('-');
    expect(items[0]?.title).toContain('Henüz');
  });

  it('builds notifications and approval summaries from approval rows only', () => {
    const approvalRows = [
      {
        approval_id: 'apr_1',
        run_id: 'run_1',
        target_kind: 'device_action',
        created_at: '2026-03-08T09:31:00Z',
      },
    ];

    expect(buildNotificationItems({ approvalRows, timeline: [], dismissedIds: [], formatClock: clock })).toEqual([
      {
        id: 'approval-apr_1',
        kind: 'warning',
        title: 'Onay talebi oluşturuldu',
        subtitle: 'device_action',
        time: '09:31',
      },
    ]);
    expect(buildPendingApprovalSummaries(approvalRows, 'run_fallback')[0]).toMatchObject({
      id: 'apr_1',
      title: 'device_action',
      subtitle: 'run_1',
    });
  });

  it('reports missing resource metrics honestly', () => {
    const systemHealth = buildSystemHealthSummary({
      coreMode: 'auto',
      handshakeRecord: { contractVersion: '2.0' },
      doctor: { status: 'ok' },
      metricsPayload: { approval_queue: { pending: 1 } },
    });
    const summary = buildRuntimeSummaryItems({
      snapshot: baseSnapshot,
      selectedRunId: 'run_1',
      hasApproval: false,
      stageLabel: 'Planlama',
      systemHealth,
    });

    expect(systemHealth.memoryUsagePct).toBeNull();
    expect(summary.find((item) => item.id === 'resources')?.text).toBe('Kaynak metrikleri henüz alınmadı.');
  });

  it('normalizes real metrics when they are present', () => {
    expect(
      buildSystemHealthSummary({
        coreMode: 'bundled',
        handshakeRecord: { contract_version: '2.1' },
        doctor: { status: 'degraded' },
        metricsPayload: {
          system: {
            memory_usage_pct: '42%',
            cpu_usage_pct: 0.18,
            disk_usage_pct: 27,
            network: { status: 'Healthy' },
          },
        },
      }),
    ).toMatchObject({
      health: 'Degraded',
      memoryUsagePct: 42,
      cpuUsagePct: 18,
      diskUsagePct: 27,
      networkStatus: 'Healthy',
    });
  });
});
