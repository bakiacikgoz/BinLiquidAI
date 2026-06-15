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
- Model provider calls write redacted governance envelopes only; prompts are pattern-redacted before evidence persistence.

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

## Vision Runtime Privacy

- Vision observations always include a screenshot hash.
- Raw screenshot paths remain `null` by default.
- Raw screenshot persistence requires explicit runtime configuration and request opt-in; current foundation tests assert zero persisted screenshots.
- Replay artifacts expose redacted event summaries and hash-chain integrity, not raw screen content.
- Secret-like, password, payment, and security indicators trigger fail-closed policy decisions instead of logging or typing sensitive data.
## Vision Runtime Privacy

Vision-first computer-use stores screenshot hashes and redacted event metadata by default. Raw screenshot persistence is disabled by default, `raw_screenshot_max_count=0`, and replay/audit artifacts must report `raw_screenshot_persisted_count=0` unless an explicit local debug policy is enabled.

Provider output is treated as untrusted observed content. Screen text is not accepted as an instruction, and sensitive indicators are propagated to policy stops rather than recorded as raw secrets.

## Cross-Platform Vision Privacy

- The platform matrix requires raw screenshot persistence to remain disabled by default.
- Platform qualification reports may reference evidence, but must not require persisted raw screenshots for the default gate.
- Operator capability payloads expose readiness, blockers, and hashes, not screen captures.
- macOS fixture reports store local fixture paths, redacted event logs,
  hash-chain audit metadata, opt-in metadata, and
  `rawScreenshotPersistedCount=0`; they do not store raw screenshots by
  default.
- Phase 4D provider readiness uses a generated synthetic local fixture image
  and validates strict JSON before any desktop capture or input. The synthetic
  image is not persisted as raw screenshot evidence.
- Phase 4E preserves that boundary: provider checks use synthetic image bytes
  only for local inference, live capture uses temporary files only when all
  one-run gates pass, and default qualification artifacts keep
  `rawScreenshotPersistedCount=0`.

## Model Provider Privacy

- Local providers remain the default path.
- Remote provider calls are opt-in through `remote_providers_enabled`.
- Public cloud providers can receive `public` data only under the default policy.
- `secret`, `credential`, `payment`, and `raw_pii` data classes are blocked before provider dispatch.
- Provider evidence envelopes include hashes, reason codes, redaction summaries, attempts, and usage metadata; they must not include raw API keys or bearer tokens.
- Native provider adapters store hash-only evidence. OpenAI Responses forces `store=false`; Anthropic Messages rejects raw payload persistence and records only hashes, normalized block metadata, stop reasons, policy decisions, and usage summaries.
