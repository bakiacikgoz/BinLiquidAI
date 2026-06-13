# Memory Privacy And Retention

Governed Memory v1 stores redacted summaries plus hashes. It does not store raw prompts, raw responses, or raw candidate text.

Privacy controls:

- Secret-like content is denied before persistence.
- Email, phone, and high-risk token patterns are redacted from candidate summaries.
- Evidence records include hashes, policy decisions, scope, visibility, and artifact references only.
- Operator Panel renders aggregate governance state, not raw memory content.

Retention:

- Records carry `retentionClass`, `ttlDays`, `expiresAt`, and `status`.
- Retrieval excludes tombstoned or expired rows.
- Tombstone operations create lifecycle evidence.

Scope rules:

- Personal private writes are allowed when policy permits.
- Agent private/agent writes are allowed when policy permits.
- Organization writes require approval.
- Cross-scope retrieval fails closed when requested scopes exceed allowed scopes.
