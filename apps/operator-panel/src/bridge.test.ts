import { describe, expect, it } from 'vitest';

import { BridgeError, handshake } from './bridge';
import { DEFAULT_SETTINGS } from './settings';

describe('bridge runtime guard', () => {
  it('fails fast when tauri runtime is unavailable', async () => {
    try {
      await handshake({ ...DEFAULT_SETTINGS });
      throw new Error('expected handshake to fail outside tauri runtime');
    } catch (error) {
      expect(error).toBeInstanceOf(BridgeError);
      if (!(error instanceof BridgeError)) {
        return;
      }
      expect(error.payload.code).toBe('CLI_FAILED');
      expect(error.payload.message).toBe('Tauri runtime not available');
      expect(error.payload.command).toBe('bridge_handshake');
      expect(error.payload.retryable).toBe(false);
    }
  });
});
