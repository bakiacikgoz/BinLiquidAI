const REQUIRED_COMMAND_KEYS = [
  'teamListJson',
  'teamReplayJson',
  'approvalShowJson',
  'approvalPendingJson',
  'approvalDecide',
  'approvalExecute',
] as const;

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}

function readString(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  return typeof value === 'string' ? value : null;
}

export function hasContractMismatch(handshakeData: unknown): boolean {
  if (!handshakeData) {
    return false;
  }

  const handshake = asRecord(handshakeData);
  const capabilities = asRecord(handshake.capabilities);
  const commandCapabilities = asRecord(capabilities.commands);

  if (readString(capabilities, 'contractVersion') !== '1.0') {
    return true;
  }

  return REQUIRED_COMMAND_KEYS.some((key) => commandCapabilities[key] !== true);
}
