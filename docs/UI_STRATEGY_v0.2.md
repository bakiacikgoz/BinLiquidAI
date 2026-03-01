# UI_STRATEGY_v0.2

## Decision

v0.2 is CLI-first. Desktop thin-shell UI is explicitly deferred.

## Why

- Reliability and benchmark quality are the v0.2 primary goals.
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
- `final`
- `warning`
- `error`

This is the compatibility bridge for v0.3 thin-shell work.
