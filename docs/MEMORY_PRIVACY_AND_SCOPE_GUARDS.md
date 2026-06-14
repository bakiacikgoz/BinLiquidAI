# Memory Privacy and Scope Guards

Semantic memory uses Workspace Memory Authority as the policy boundary. The search service never performs a broad vector search and then treats post-filtering as the only safety step. It first builds the allowed record set from scope-level RBAC decisions, then scores only those records.

Guardrails:

- `raw_persistence` is validated as false.
- Embeddings are generated from redacted summaries only.
- Secret-like embedding inputs are blocked.
- Search evidence contains query hashes and hit ids, not raw query text.
- Expired and tombstoned records are excluded.
- Stale indexes are blocked unless stale reads are explicitly allowed.

Validate with:

```bash
make memory-privacy-leakage-gate
```
