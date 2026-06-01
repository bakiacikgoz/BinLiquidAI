import { describe, expect, it } from 'vitest';

import { formatReasonCode, reasonCodeMessages } from './reasonCodes';

describe('reason code localization', () => {
  it('keeps English and Turkish reason code dictionaries in parity', () => {
    expect(Object.keys(reasonCodeMessages.tr).sort()).toEqual(Object.keys(reasonCodeMessages.en).sort());
  });

  it('formats internal reason codes with human explanations', () => {
    expect(formatReasonCode('MACOS_LIVE_DISABLED', 'en')).toContain('macOS live computer-use is disabled');
    expect(formatReasonCode('MACOS_LIVE_DISABLED', 'tr')).toContain('macOS canlı computer-use');
    expect(formatReasonCode('UNKNOWN_NEW_REASON', 'en')).toContain('Unknown New Reason');
  });
});
