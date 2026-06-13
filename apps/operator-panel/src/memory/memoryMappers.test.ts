import { describe, expect, it } from 'vitest';
import { mapMemoryGovernance } from './memoryMappers';
import type { MemoryAuthoritySnapshot } from '../control-plane/types';

describe('memory governance mappers', () => {
  it('keeps raw persistence and index readiness visible', () => {
    const snapshot: MemoryAuthoritySnapshot = {
      contractVersion: 'memory.authority-snapshot/v1',
      enabled: true,
      authorityStatus: 'pass',
      storeSchemaVersion: 'memory.v3',
      records: {
        active: 2,
        expired: 0,
        tombstoned: 0,
        deniedWrites: 1,
        pendingProposals: 1,
      },
      scopes: [
        {
          scope: 'personal',
          visibility: 'private',
          activeRecords: 2,
          policy: 'allow',
        },
      ],
      index: {
        backend: 'sqlite_text',
        status: 'pass',
        recordCount: 2,
        lastRebuildAt: null,
        degradedReason: null,
        blockingReasons: [],
        experimental: false,
      },
      privacy: {
        rawPromptPersistence: false,
        rawResponsePersistence: false,
        primaryUiRawContent: false,
      },
      evidence: {
        mode: 'hash_only_redacted',
        lastArtifactRef: 'artifacts/memory-governance/latest.json',
      },
      blockingReasons: [],
      warnings: [],
    };

    const model = mapMemoryGovernance(snapshot);

    expect(model.status).toBe('pass');
    expect(model.badges.map((item) => item.label)).toContain('raw_persistence_off');
    expect(model.rows[0]).toMatchObject({ label: 'personal', status: '2 active' });
  });
});
