import { describe, expect, it } from 'vitest';

import {
  getComputerUseSessionState,
  handshake,
  isBridgePreviewMode,
  isPreviewAllowedForEnv,
  listRuns,
  pauseComputerUseSession,
  readArtifact,
  resumeComputerUseSession,
  resolveConfig,
  showApproval,
  stopComputerUseSession,
  submitComputerUseRun,
  submitTeamRun,
  tailEvents,
} from './bridge';
import { DEFAULT_SETTINGS } from './settings';

describe('bridge preview fallback', () => {
  it('requires dev, test, or explicit env flag for browser preview mode', () => {
    expect(isPreviewAllowedForEnv({ MODE: 'production', DEV: false })).toBe(false);
    expect(isPreviewAllowedForEnv({ MODE: 'production', DEV: false, VITE_OPERATOR_PANEL_PREVIEW: '1' })).toBe(true);
    expect(isPreviewAllowedForEnv({ MODE: 'test', DEV: false })).toBe(true);
    expect(isPreviewAllowedForEnv({ MODE: 'production', DEV: true })).toBe(true);
  });

  it('returns preview handshake data when tauri runtime is unavailable', async () => {
    expect(isBridgePreviewMode()).toBe(true);

    const payload = await handshake({ ...DEFAULT_SETTINGS });
    const record = payload as Record<string, unknown>;
    const capabilities = record.capabilities as Record<string, unknown>;

    expect(record.coreVersion).toBe('0.6.0-preview');
    expect(record.contractVersion).toBe('2.0');
    expect(capabilities.previewMode).toBe(true);
  });

  it('returns preview submit payloads for task workspace actions', async () => {
    const [teamPayload, computerUsePayload] = await Promise.all([
      submitTeamRun(
        { ...DEFAULT_SETTINGS },
        {
          specPath: 'examples/team/restricted_pilot.yaml',
          request: 'inspect queue',
        },
      ),
      submitComputerUseRun(
        { ...DEFAULT_SETTINGS },
        {
          request: 'open "https://preview.aegis.local/form"',
          mode: 'step_approval',
        },
      ),
    ]);

    const teamRecord = teamPayload as Record<string, unknown>;
    expect(teamRecord.contractVersion).toBe('2.0');
    expect(teamRecord.jobId).toBe('job-ui-preview-1');

    const computerUseRecord = computerUsePayload as Record<string, unknown>;
    expect(computerUseRecord.contractVersion).toBe('2.0');
    expect(computerUseRecord.jobId).toBe('job-ui-preview-cu-1');
  });

  it('returns preview control payloads for computer-use sessions', async () => {
    const [pause, resume, stop, state] = await Promise.all([
      pauseComputerUseSession({ ...DEFAULT_SETTINGS }, 'job-ui-preview-cu-1'),
      resumeComputerUseSession({ ...DEFAULT_SETTINGS }, 'job-ui-preview-cu-1'),
      stopComputerUseSession({ ...DEFAULT_SETTINGS }, 'job-ui-preview-cu-1'),
      getComputerUseSessionState({ ...DEFAULT_SETTINGS }, 'job-ui-preview-cu-1'),
    ]);

    expect((pause as Record<string, unknown>).requested).toBe('pause');
    expect((pause as Record<string, unknown>).outcome).toBe('rejected');
    expect((resume as Record<string, unknown>).requested).toBe('resume');
    expect((resume as Record<string, unknown>).reason).toBe('approval_not_executed');
    expect((stop as Record<string, unknown>).requested).toBe('stop');
    expect((stop as Record<string, unknown>).outcome).toBe('accepted');
    expect(((state as Record<string, unknown>).computer_use as Record<string, unknown>).stage).toBe(
      'require_approval',
    );
    expect(((state as Record<string, unknown>).recovery as Record<string, unknown>).resume_allowed).toBe(
      false,
    );
  });

  it('returns preview config resolve payload for system workspace', async () => {
    const payload = await resolveConfig({ ...DEFAULT_SETTINGS });
    const record = payload as Record<string, unknown>;
    expect(record.contract_version).toBe('2.0');
    expect(record.status).toBe('ok');
    expect((record.resolved as Record<string, unknown>).profile_name).toBe(DEFAULT_SETTINGS.profile);
  });

  it('returns runtime-shaped preview payloads for approvals and runs', async () => {
    const [approval, runs, artifact, events] = await Promise.all([
      showApproval({ ...DEFAULT_SETTINGS }, 'apr_preview'),
      listRuns({ ...DEFAULT_SETTINGS }),
      readArtifact({ ...DEFAULT_SETTINGS }, 'job-preview', 'status.json'),
      tailEvents({ ...DEFAULT_SETTINGS }, 'job-preview', 0),
    ]);

    const approvalRecord = approval as Record<string, unknown>;
    expect(approvalRecord.contract_version).toBe('2.0');
    expect((approvalRecord.ticket as Record<string, unknown>).approval_id).toBe('apr_preview');

    const runRecord = runs as Record<string, unknown>;
    expect(runRecord.contract_version).toBe('2.0');
    expect(runRecord.count).toBeGreaterThan(0);

    const artifactRecord = artifact as Record<string, unknown>;
    expect(artifactRecord.contractVersion).toBe('2.0');
    expect(artifactRecord.artifactName).toBe('status.json');
    expect(
      ((artifactRecord.payload as Record<string, unknown>).computer_use as Record<string, unknown>).stage,
    ).toBe('require_approval');

    expect(events.contractVersion).toBe('2.0');
    expect(events.events.length).toBeGreaterThan(0);
  });
});
