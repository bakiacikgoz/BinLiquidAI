# UI_STRATEGY_v0.3

## Decision

v0.3 keeps a CLI-first core. Desktop thin-shell UI is still deferred.

## Why

- Reliability and governance correctness are the v0.3 primary goals.
- CLI already exposes structured output modes for future IPC/UI integration.
- Deferring UI avoids coupling regressions in product path.

## Prepared Interfaces

`chat` command supports:

- `--json`
- `--json-stream`
- `--stdio-json`

Event vocabulary for stream mode:

- `token`
- `status`
- `router_decision`
- `expert_start`
- `expert_end`
- `policy_decision`
- `approval_pending`
- `audit_artifact`
- `final`
- `warning`
- `error`

This is the compatibility bridge for v0.3 thin-shell work.
