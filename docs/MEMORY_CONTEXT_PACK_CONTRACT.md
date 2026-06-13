# Memory Context Pack Contract

`MemoryContextPack` is the only memory object allowed into prompt construction.

Required invariants:

- `version` is `memory.context-pack/v1`.
- `rawContentIncluded` is always `false`.
- Hits contain `redactedSummary`, `contentHash`, scope, visibility and score.
- Pack size is bounded by `memory.runtime.max_context_chars`.
- Retrieval evidence is referenced by `evidenceRef` when available.

The prompt section is labelled as untrusted context and must not be treated as instructions.
