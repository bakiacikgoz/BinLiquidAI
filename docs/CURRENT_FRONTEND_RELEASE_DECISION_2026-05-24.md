# Current Frontend Release Decision - 2026-05-24

Status: FRONTEND FUNCTIONAL GATE GREEN

This decision supersedes the earlier frontend-only blocker list that said AI
Assistant model selection was not wired. The 2026-05-23 release readiness
snapshot remains a separate date-specific artifact.

## Current state

Operator Panel frontend functional completion is green for Faz 2, Faz 3, and
Faz 4 scope.

Evidence:

- `artifacts/operator-panel-ui/FRONTEND_FUNCTIONAL_GAP_REPORT.md`
- `artifacts/operator-panel-ui/qa-summary.md`
- `artifacts/operator-panel-ui/tauri-bridge-smoke.json`
- `artifacts/operator-panel-ui/live-cli-smoke.json`

## Closed frontend blockers

- AI Assistant provider/model/fallback/HF model selection is wired.
- Assistant composer no longer exposes the hard-coded disabled `AegisOS-Pro`
  model control.
- `useAssistantSession` passes provider, fallback provider, model, and HF model
  ID into `startAssistantTurn` options.
- Placeholder/no-op/release-blocking dead controls are cleared from the audited
  UI surface.
- Page-level control inventory has 0 critical, 0 high, and 0 medium findings.

## UI functional QA status

- Total controls: 127.
- Working controls: 99.
- Disabled with explicit reason: 28.
- Removed until ready: 0.
- Missing handlers: 0.
- No-op handlers: 0.
- Disabled without explicit reason: 0.
- Controls with test coverage evidence: 127/127.

## Bridge confidence

- Preview E2E: PASS.
- Bridge unit tests: PASS.
- Tauri bridge smoke: PASS.
- Live CLI smoke: PASS for read-only capabilities/config commands.

The live Tauri desktop window was not used to claim unrestricted automation or
real model execution. The bridge confidence is based on TypeScript invoke
contract tests, Rust bridge tests, command-argument validation, stdio-json event
parsing smoke, and read-only CLI smoke.

## Green gates

- `corepack pnpm --dir apps/operator-panel qa:frontend`: PASS.
- `cargo test -q --manifest-path apps/operator-panel/src-tauri/Cargo.toml`:
  PASS, 23 tests.
- `uv run python -m binliquid operator capabilities --json`: PASS.
- `uv run python -m binliquid config resolve --profile balanced --json`: PASS.

## Remaining no-ship boundaries

- Do not claim unrestricted live computer-use automation.
- Do not claim live assistant execution against a real provider/model from this
  frontend decision alone.
- Do not treat preview E2E as proof of a launched production Tauri desktop app.
- Do not ship public desktop artifacts without the existing signing,
  notarization, clean-machine, and promote-gate evidence required by the main
  release decision.

## Next single blocker to close

For full live Tauri confidence, run a launched Tauri dev/debug smoke that
exercises bridge handshake, config resolve, capabilities read, and assistant
start-turn event flow from the actual desktop shell.
