import type { MemoryAuthoritySnapshot } from '../control-plane/types';

export type MemoryGovernanceMetric = {
  label: string;
  value: string | number;
  detail: string;
};

export type MemoryGovernanceBadge = {
  label: string;
  tone: 'good' | 'warn' | 'bad' | 'neutral';
};

export type MemoryGovernanceRow = {
  id: string;
  label: string;
  meta: string;
  status: string;
};

export type MemoryGovernanceViewModel = {
  status: string;
  generatedDetail: string;
  metrics: MemoryGovernanceMetric[];
  badges: MemoryGovernanceBadge[];
  rows: MemoryGovernanceRow[];
  warnings: string[];
  blockingReasons: string[];
};

export function mapMemoryGovernance(snapshot?: MemoryAuthoritySnapshot | null): MemoryGovernanceViewModel {
  if (!snapshot) {
    return emptyMemoryGovernanceModel('snapshot_missing');
  }

  const rawPersistenceOff =
    !snapshot.privacy.rawPromptPersistence &&
    !snapshot.privacy.rawResponsePersistence &&
    !snapshot.privacy.primaryUiRawContent;

  return {
    status: snapshot.authorityStatus,
    generatedDetail: `${snapshot.contractVersion} / ${snapshot.storeSchemaVersion}`,
    metrics: [
      { label: 'Active records', value: snapshot.records.active, detail: 'retrievable memory rows' },
      { label: 'Pending proposals', value: snapshot.records.pendingProposals, detail: 'approval-gated writes' },
      { label: 'Index backend', value: snapshot.index.backend, detail: snapshot.index.status },
      { label: 'Evidence mode', value: snapshot.evidence.mode, detail: snapshot.evidence.lastArtifactRef ?? 'no artifact yet' },
    ],
    badges: [
      {
        label: snapshot.enabled ? 'memory_v3_enabled' : 'memory_v3_disabled',
        tone: snapshot.enabled ? 'good' : 'neutral',
      },
      {
        label: rawPersistenceOff ? 'raw_persistence_off' : 'raw_persistence_blocked',
        tone: rawPersistenceOff ? 'good' : 'bad',
      },
      {
        label: `index_${snapshot.index.status}`,
        tone: snapshot.index.status === 'pass' || snapshot.index.status === 'disabled' ? 'good' : 'warn',
      },
      { label: 'hash_only_redacted', tone: 'good' },
    ],
    rows:
      snapshot.scopes.length > 0
        ? snapshot.scopes.map((item) => ({
            id: `${item.scope}:${item.visibility}`,
            label: item.scope,
            meta: `${item.visibility} / ${item.policy}`,
            status: `${item.activeRecords} active`,
          }))
        : [
            {
              id: 'empty-memory-scope',
              label: 'No scoped records',
              meta: snapshot.index.degradedReason ?? 'authority initialized',
              status: snapshot.authorityStatus,
            },
          ],
    warnings: snapshot.warnings,
    blockingReasons: snapshot.blockingReasons.concat(snapshot.index.blockingReasons),
  };
}

function emptyMemoryGovernanceModel(reason: string): MemoryGovernanceViewModel {
  return {
    status: 'disabled',
    generatedDetail: 'memory.authority-snapshot/v1 / memory.v3',
    metrics: [
      { label: 'Active records', value: 0, detail: reason },
      { label: 'Pending proposals', value: 0, detail: reason },
      { label: 'Index backend', value: 'sqlite_text', detail: 'disabled' },
      { label: 'Evidence mode', value: 'hash_only_redacted', detail: 'no artifact yet' },
    ],
    badges: [
      { label: 'memory_v3_disabled', tone: 'neutral' },
      { label: 'raw_persistence_off', tone: 'good' },
      { label: 'index_disabled', tone: 'good' },
      { label: 'hash_only_redacted', tone: 'good' },
    ],
    rows: [{ id: 'empty-memory-scope', label: 'No scoped records', meta: reason, status: 'disabled' }],
    warnings: [reason],
    blockingReasons: [],
  };
}
