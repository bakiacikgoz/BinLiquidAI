# Computer-Use Privacy Boundary

## Defaults

Computer-use privacy defaults are fail-closed:

- raw screenshots are not persisted
- `raw_screenshot_persistence=false`
- `raw_screenshot_max_count=0`
- replay stores hashes and redacted metadata
- support bundles exclude raw screenshots by default

## Raw Screenshot Policy

Raw screenshots may be captured in memory as part of observation, but they are not written to disk by default. Debug persistence requires explicit local opt-in and a bounded count.

Sensitive surfaces must stop before execution and must not persist raw screenshots.

## Replay Evidence

Replay evidence proves trace integrity, hash-chain continuity, approval boundaries, and redaction policy. It does not prove business correctness or general desktop reliability.
