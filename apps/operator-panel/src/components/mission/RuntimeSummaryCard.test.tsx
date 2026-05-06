import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { redactJson } from '../../redactJson';
import { RuntimeSummaryCard } from './RuntimeSummaryCard';
import type { ComputerUseCapabilityResolution } from '../../capabilities';

describe('RuntimeSummaryCard', () => {
  it('does not render raw JSON by default', () => {
    const html = renderToStaticMarkup(
      <RuntimeSummaryCard
        items={[{ id: 'summary', tone: 'success', text: 'Çalışma bağlamı doğrulandı.' }]}
        rawJson={{ secret_payload: 'SECRET_VALUE' }}
      />,
    );

    expect(html).toContain('Ham JSON');
    expect(html).toContain('disabled=""');
    expect(html).not.toContain('secret_payload');
    expect(html).not.toContain('SECRET_VALUE');
  });

  it('can render redacted raw JSON only when debug disclosure state is open', () => {
    const html = renderToStaticMarkup(
      <RuntimeSummaryCard
        debugRawEnabled
        defaultShowRaw
        items={[{ id: 'summary', tone: 'success', text: 'Çalışma bağlamı doğrulandı.' }]}
        rawJson={{ raw_visible: true, api_token: 'SECRET_VALUE' }}
      />,
    );

    expect(html).toContain('raw_visible');
    expect(html).toContain('[redacted]');
    expect(html).not.toContain('SECRET_VALUE');
  });

  it('redacts nested sensitive keys before rendering', () => {
    expect(redactJson({ nested: { password: 'SECRET_VALUE' }, safe: 'ok' })).toEqual({
      nested: { password: '[redacted]' },
      safe: 'ok',
    });
  });

  it('renders risk badges and redacts raw screenshot paths in debug JSON', () => {
    const html = renderToStaticMarkup(
      <RuntimeSummaryCard
        debugRawEnabled
        defaultShowRaw
        items={[{ id: 'vision-action', tone: 'warning', text: 'Vision action: click submit_button.', badge: 'medium' }]}
        rawJson={{
          computer_use: {
            steps: [
              {
                action: {
                  action_type: 'click',
                  raw_screenshot_path: '/tmp/private-screen.png',
                },
              },
            ],
          },
        }}
      />,
    );

    expect(html).toContain('medium');
    expect(html).toContain('mc-badge-warning');
    expect(html).toContain('raw_screenshot_path');
    expect(html).toContain('[redacted]');
    expect(html).not.toContain('/tmp/private-screen.png');
  });

  it('renders read-only computer-use capability resolver status without raw paths', () => {
    const capabilityResolution = {
      schemaVersion: 1,
      platform: 'windows',
      profile: 'balanced',
      status: 'blocked',
      liveEnabled: false,
      supervisedLiveAllowed: false,
      publicLiveClaimAllowed: false,
      reasonCode: 'WINDOWS_COMPUTER_USE_NOT_QUALIFIED',
      blockers: ['COMPUTER_USE_EVIDENCE_MISSING'],
      evidence: {
        status: 'missing',
        source: 'none',
        fresh: false,
        commitMatch: false,
        configMatch: false,
        providerMatch: false,
        backendMatch: false,
        rawScreenshotPath: 'C:/Users/duzey/private-screen.png',
      },
      config: {
        visionEnabled: false,
        provider: 'none',
        captureBackend: 'disabled',
        inputBackend: 'disabled',
        rawScreenshotPersistence: false,
        terminalPolicy: 'deny',
      },
      driver: {
        ready: false,
        captureReady: false,
        inputReady: false,
        permissionReady: false,
      },
      safety: {
        failClosed: true,
        rawScreenshotPersistenceAllowed: false,
        requiresStepApproval: true,
        sensitiveSurfaceStopEnabled: true,
      },
    } as unknown as ComputerUseCapabilityResolution;

    const html = renderToStaticMarkup(
      <RuntimeSummaryCard
        items={[{ id: 'summary', tone: 'warning', text: 'Computer-use qualification is blocked.' }]}
        rawJson={{}}
        computerUseCapabilityResolution={capabilityResolution}
      />,
    );

    expect(html).toContain('Computer-use capability');
    expect(html).toContain('Live execution');
    expect(html).toContain('Disabled');
    expect(html).toContain('WINDOWS_COMPUTER_USE_NOT_QUALIFIED');
    expect(html).toContain('COMPUTER_USE_EVIDENCE_MISSING');
    expect(html).toContain('Evidence');
    expect(html).toContain('missing');
    expect(html).toContain('Public live claim');
    expect(html).not.toContain('C:/Users/duzey');
    expect(html).not.toContain('Start live');
  });
});
