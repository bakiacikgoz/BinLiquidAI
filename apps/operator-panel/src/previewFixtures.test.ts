import { describe, expect, it } from 'vitest';

import {
  previewArtifact,
  previewConfigResolve,
  previewControlPlaneSnapshot,
  previewHandshake,
  previewIdentity,
  previewRunDetail,
  previewRunReplay,
  previewRunSummary,
  previewSubmitResponse,
} from './previewFixtures';
import { DEFAULT_SETTINGS } from './settings';

describe('preview runtime paths', () => {
  it('serializes fixtures without legacy state paths and replaces the team root', () => {
    const legacyStateRoot = ['.', 'bin', 'liquid'].join('');
    const customRoot = '.imperaos/custom-preview/jobs';
    const settings = { ...DEFAULT_SETTINGS, rootDir: customRoot };
    const payloads = [
      previewHandshake(settings),
      previewSubmitResponse(settings),
      previewRunSummary(settings),
      previewRunDetail(settings),
      previewRunReplay(),
      previewArtifact(settings, 'job-ui-preview-1', 'audit_envelope.json'),
      previewConfigResolve(settings),
      previewIdentity(settings),
      previewControlPlaneSnapshot(settings),
    ];
    const serialized = JSON.stringify(payloads);

    expect(serialized).not.toContain(legacyStateRoot);
    expect(JSON.stringify(previewRunSummary(settings))).toContain(customRoot);
    expect(JSON.stringify(previewRunDetail(settings))).toContain(customRoot);
    expect(JSON.stringify(previewControlPlaneSnapshot(settings))).toContain(
      '.imperaos/control-plane',
    );
  });
});
