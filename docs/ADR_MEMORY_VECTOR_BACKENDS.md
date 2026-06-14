# ADR: Memory Vector Backends

## Status

Accepted for v1 local implementation.

## Decision

Use `in_memory_fixture` as the default semantic backend. It persists only redacted summary hashes, content hashes, deterministic fixture vectors, and manifest metadata under local artifacts.

Keep `sqlite_text` as a local-compatible backend alias and keep `turbovec` optional and experimental.

## Rationale

The first requirement is governed retrieval quality and leakage safety, not high-scale vector infrastructure. A deterministic local backend gives reproducible tests, stable gates, and no new dependency or network listener.

## Consequences

- Default profiles remain disabled.
- Runtime injection remains disabled unless explicitly opted in.
- Missing TurboVec dependency is non-fatal.
- Future vector backends must implement pre-filtered candidate authorization before scoring.
