import { describe, expect, it } from 'vitest';

import { handshake, isBridgePreviewMode } from './bridge';
import { DEFAULT_SETTINGS } from './settings';

describe('bridge preview fallback', () => {
  it('returns preview handshake data when tauri runtime is unavailable', async () => {
    expect(isBridgePreviewMode()).toBe(true);

    const payload = await handshake({ ...DEFAULT_SETTINGS });
    const record = payload as Record<string, unknown>;
    const capabilities = record.capabilities as Record<string, unknown>;

    expect(record.coreVersion).toBe('0.5.0-preview');
    expect(record.contractVersion).toBe('2.0');
    expect(capabilities.previewMode).toBe(true);
  });
});
