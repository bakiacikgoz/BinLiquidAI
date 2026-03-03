# PRIVACY_MODEL (v0.3)

## Defaults

- `privacy_mode=true`
- `web_enabled=false`
- Persistent traces disabled unless debug is enabled and privacy is explicitly turned off.

## Telemetry Behavior

- In-memory events are always allowed for current request processing.
- In-memory event payloads can be redacted via governance PII rules.
- Disk persistence is privacy-gated.
- Router dataset JSONL writes are also privacy-gated.
- v0.3 audit artifacts are written as privacy-safe/redacted JSON envelopes.
- v0.4 team artifacts include redacted handoff payloads and hash-chained audit envelopes.

## Memory Behavior

- `lite` profile keeps persistent memory disabled.
- Memory-disabled mode should not create SQLite files.
- TTL + prune protects stale retention in enabled modes.

## Tool Safety

- Tool commands go through allowlist and sandbox runner.
- Non-allowlisted commands are rejected deterministically.
- Prompt text is never directly executed as shell.

## Regression Coverage

Covered by tests:

- no persistence under privacy mode
- memory disabled no-touch behavior
- allowlist rejection for unsafe command roots
