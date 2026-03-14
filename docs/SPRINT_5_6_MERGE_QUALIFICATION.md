# Sprint 5.6 Merge Qualification

## Real Acceptance Prereqs

- macOS with Safari installed
- `AEGISOS_ENABLE_REAL_COMPUTER_USE_TESTS=1`
- Terminal / Codex app allowed to automate Safari and System Events
- Accessibility permission granted for UI scripting
- Safari Developer setting `Allow JavaScript from Apple Events` enabled manually
- Deterministic local fixture server available on `127.0.0.1`

## Repro Commands

```bash
pnpm --dir apps/operator-panel test
pnpm --dir apps/operator-panel lint
pnpm --dir apps/operator-panel build
cargo fmt --check
cargo check
uv run ruff check binliquid/computer_use apps/operator-panel/src-tauri/src tests/test_computer_use.py tests/test_computer_use_world_model.py tests/test_computer_use_runtime.py tests/test_computer_use_acceptance.py tests/test_operator_contracts.py tests/test_team_cli.py
uv run pytest tests/test_computer_use.py tests/test_computer_use_world_model.py tests/test_computer_use_runtime.py tests/test_operator_contracts.py tests/test_team_cli.py -q
AEGISOS_ENABLE_REAL_COMPUTER_USE_TESTS=1 uv run pytest tests/test_computer_use_acceptance.py -q
```

## 2026-03-14 Qualification Result

- Environment confirmed: macOS 26.3.1, `osascript` available, Safari launchable
- Runtime blocker fixed: `launch_app` / `focus_window` no longer fail pre-action surface verification when another app is frontmost
- Real acceptance blocker remains environmental: Safari rejects `do JavaScript` until `Allow JavaScript from Apple Events` is enabled manually

Observed Safari error:

```text
You must enable 'Allow JavaScript from Apple Events' in the Developer section of Safari Settings to use 'do JavaScript'.
```

## Triage

### Blocker

- Safari Developer setting disabled
  - Severity: blocker for real acceptance, not for mergeable code correctness
  - Root cause: environment prerequisite missing on the current machine
  - Action: enable the setting manually, then rerun the real acceptance suite

### High-Value Follow-Up

- Add a doctor/preflight check that detects missing Safari `do JavaScript` capability before starting real acceptance or live browser execution

### Known Boundary

- Real Safari validation remains opt-in and permission-dependent
- Current slice is still controlled, fail-closed, and browser-centered
- Cross-platform parity and unrestricted desktop autonomy are not in scope for this release

## Operator Smoke Status

- Automated workspace/state mapping remains green via frontend tests
- Real UI smoke flows are blocked by the same Safari JavaScript automation prerequisite

## Merge Checklist

- [x] frontend build / lint / test green
- [x] cargo fmt / check green
- [x] python ruff / pytest green
- [ ] gated real acceptance passed on a machine with Safari JavaScript automation enabled
- [x] runtime blocker for desktop activation preflight fixed
- [x] known boundary note updated
