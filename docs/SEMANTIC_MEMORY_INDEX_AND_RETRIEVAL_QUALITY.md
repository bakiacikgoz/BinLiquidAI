# Semantic Memory Index and Retrieval Quality

Semantic memory is a governed retrieval layer on top of Workspace Memory Authority. It is disabled by default and never stores raw memory content, raw prompts, raw queries, PII, or secrets in index artifacts or operator evidence.

Runtime injection is governed by Agent Memory Policy Enforcement v1. Semantic retrieval must receive an already authorized workspace/scope candidate set before scoring, and `memory.runtime.semantic_runtime_mode` controls disabled, shadow, and enforced runtime behavior. See `docs/MEMORY_RUNTIME_POLICY_ENFORCEMENT.md`.

Default config:

```toml
[memory.semantic]
enabled = false
runtime_injection_enabled = false
backend = "in_memory_fixture"
embedding_profile = "deterministic-fixture-v1"
max_hits = 8
allow_stale_index = false
raw_persistence = false

[memory.semantic.backends.turbovec]
enabled = false
experimental = true
bit_width = 4
allow_runtime_injection = false
```

Retrieval order:

1. Resolve requested workspace scopes.
2. Evaluate Workspace Memory Authority RBAC for each scope.
3. Build the candidate set only from allowed, active, non-expired records.
4. Score allowed candidates with deterministic fixture embeddings, lexical overlap, and recency.
5. Emit hash-only evidence.

The runtime bridge only uses semantic search when both `memory.semantic.enabled` and `memory.semantic.runtime_injection_enabled` are true.

Primary gates:

```bash
make semantic-memory-index-gate
make memory-retrieval-quality-gate
make memory-privacy-leakage-gate
make memory-backend-benchmark-gate
```
