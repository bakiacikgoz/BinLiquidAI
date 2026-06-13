# Memory v1 Mainline Handoff

This branch builds on governed memory v1 and keeps compatibility with the legacy `MemoryManager`.

Added surfaces:

- Runtime bridge for Orchestrator and Team Runtime.
- Redacted `MemoryContextPack` prompt injection.
- Policy-gated post-run write proposals.
- File-based Memory Sync Pack export, verify and import.
- Control Plane snapshot fields: `memoryRuntime` and `memorySync`.
- Operator Panel route: Memory Runtime.

Required gates before release:

```bash
make governed-memory-v1-gate
make memory-context-pack-gate
make memory-runtime-gate
make memory-sync-gate
make pilot-readiness-gate
```
