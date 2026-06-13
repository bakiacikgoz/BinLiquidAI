# Memory V1 Discovery

Discovery date: 2026-06-13.

Existing memory subsystem:

- Legacy local store: `binliquid/memory/persistent_store.py`.
- Manager and salience gate: `binliquid/memory/manager.py`, `salience_gate.py`.
- Existing tests cover concurrency, TTL, dedupe, migration, scope store behavior, and team fail-closed memory.

Implemented additive layer:

- Models: `binliquid/memory/models.py`.
- Store: `binliquid/memory/store_v3.py`.
- Policy/redaction/evidence: `policy.py`, `redaction.py`, `evidence.py`.
- Authority: `authority.py`.
- Index adapters: `indexes/`.
- Control Plane snapshot and Operator Panel route: `memoryGovernance`, `Memory Governance`.

No destructive migration is required. The new SQLite tables are additive and the feature remains disabled by default.
