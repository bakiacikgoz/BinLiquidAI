# Memory Index Backends

`sqlite_text` is the default backend. It uses the authoritative SQLite store and does not require external services.

`dense_json` is deterministic and local. It is intended for tests, benchmarks, and fallback experiments, not production ranking claims.

`turbovec_experimental` is optional and disabled by default. The adapter must report `disabled` or `unavailable` unless explicitly enabled and importable.

Backend contract:

- `status()` returns backend name, status, record count, degraded reason, blockers, and experimental flag.
- `add()` and `rebuild()` accept only redacted summaries.
- `search()` must respect scope and visibility filters before scoring.
- No backend may persist raw prompts, raw responses, or unredacted candidate text.
