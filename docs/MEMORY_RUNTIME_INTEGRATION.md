# Memory Runtime Integration

Memory runtime is opt-in. `memory.v3_enabled` and `memory.runtime.enabled` must both be true before runtime prompts receive memory context.

Runtime reads go through `MemoryRuntimeBridge.retrieve_context()` and return a `MemoryContextPack`. The prompt injector only uses redacted summaries, scope, visibility and hashes. Raw memory content is not included in prompts, UI snapshots or artifacts.

Post-run writes go through `MemoryRuntimeBridge.propose_post_run_write()` when `memory.runtime.post_run_write_enabled=true`. The bridge creates a `MemoryWriteProposal`; `MemoryAuthority` decides whether the result is written, proposal-only, approval-required, denied or conflicted.

Legacy `MemoryManager` remains the fallback path when runtime memory is disabled.
