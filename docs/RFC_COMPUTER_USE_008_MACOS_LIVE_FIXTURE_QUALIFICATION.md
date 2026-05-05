# RFC 008: macOS Live Fixture Qualification

## Status

Implemented as a fail-closed evidence gate. This phase does not enable
unrestricted desktop automation.

## Scope

Phase 4B qualifies only supervised local macOS fixtures:

- `local_browser_form`
- `textedit_safe_typing`
- `finder_fixture_file`
- `sensitive_surface_stop`
- `terminal_deny`

The report scope is `supervised_local_fixtures`. Windows and Linux remain not
qualified for live execution.

## Required Opt-In

The live fixture command must see both environment values:

```text
BINLIQUID_COMPUTER_USE_LIVE_OPT_IN=I_UNDERSTAND_THIS_CONTROLS_MY_MAC
BINLIQUID_COMPUTER_USE_LIVE_MACOS=1
```

Without those exact values, the report is `blocked` and all fixtures remain
`skipped`.

## Report And Replay

The canonical report path is:

```text
artifacts/computer_use/macos_qualification_report.json
```

The report includes host metadata, provider readiness, permission states,
fixture results, local fixture artifact paths, redacted event log path, replay
audit path, limitations, blockers, and safety invariants. Raw screenshot
persistence must remain `0`.

Replay verification:

```bash
uv run binliquid computer-use replay \
  --report artifacts/computer_use/macos_qualification_report.json \
  --verify \
  --json
```

For blocked reports this command exits non-zero because `report_status_pass` is
false, while policy checks such as raw screenshot persistence and hash-chain
integrity may still pass.

## Operator Stages

- `fixture_qualified`: a fresh matching local fixture report exists, but
  `macos_live_enabled=false`.
- `permission_ready`: local permissions and input/capture are ready, but the
  provider is not ready.
- `provider_ready`: provider is ready, but fresh qualification evidence is
  missing or invalid.
- `qualified_limited`: all macOS gates pass and `liveEnabled=true`.

Any missing opt-in, stale report, commit/config mismatch, missing permission,
disabled backend, unsafe screenshot policy, terminal policy drift, or sensitive
surface policy drift keeps the runtime fail-closed.
