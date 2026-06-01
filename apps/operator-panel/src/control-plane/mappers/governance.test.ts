import { describe, expect, it } from 'vitest';

import previewSnapshotFixture from '../../../../../contracts/operator_panel/fixtures/control_plane_snapshot_preview.json';
import type { ControlPlaneSnapshot } from '../types';
import {
  buildAlertsPageModel,
  buildLogsPageModel,
  buildPolicyPacksPageModel,
  buildReportsPageModel,
  buildRolesPageModel,
  buildUsersPageModel,
} from './governance';

const previewSnapshot = previewSnapshotFixture as ControlPlaneSnapshot;

describe('governance page mappers', () => {
  it('maps snapshot logs, reports, alerts, and policy packs into table rows', () => {
    expect(buildLogsPageModel(previewSnapshot, { events: [], runItems: [] }).rows[0]?.title).toContain(
      'snapshot generated',
    );
    expect(buildReportsPageModel(previewSnapshot, { operationOutputs: {}, claims: {} }).rows[0]?.title).toContain(
      'Qualification report',
    );
    expect(buildAlertsPageModel(previewSnapshot, { driftEvents: [], pendingApprovals: [], claims: {} }).rows[0]?.status).toContain(
      'active',
    );
    expect(buildPolicyPacksPageModel(previewSnapshot, {}).rows[0]).toMatchObject({
      id: 'preview-policy',
      status: 'active',
    });
  });

  it('maps admin users and roles from the snapshot instead of static placeholder rows', () => {
    const users = buildUsersPageModel(previewSnapshot, '', 'balanced');
    const roles = buildRolesPageModel(previewSnapshot, 'balanced');

    expect(users.rows[0]).toMatchObject({
      id: 'preview-operator',
      status: 'active',
    });
    expect(roles.rows[0]).toMatchObject({
      id: 'viewer',
    });
  });
});
