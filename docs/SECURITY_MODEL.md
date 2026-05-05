# SECURITY_MODEL (v0.3)

## Default Posture

- Web access disabled by default
- Privacy mode enabled by default
- Persistent traces only when debug is on and privacy is explicitly disabled
- Tool execution constrained by allowlist + sandbox runner
- Governance policy defaults to fail-closed for execution commands

## Tool Allowlist

Allowed command roots:

- `python`
- `uv`
- `pytest`
- `ruff`
- `rg`

Commands outside allowlist are rejected with deterministic error (`exit_code=126`).

## Runtime Guardrails

- `max_tool_calls` enforced per request
- `max_recursion_depth` enforced per session context
- expert timeout + retry limits
- circuit breaker cooldown for repeated expert failures
- task/tool policy evaluation (`allow|deny|require_approval`)
- handoff/memory-scope policy evaluation (`allow|deny|require_approval`)
- async approval queue with audit trail

## Prompt/Tool Injection Defense

- Planner output must validate strict schema
- Invalid planner output triggers deterministic fallback reason code
- Document content is treated as content, never as executable shell command
- Tool runner only accepts explicit allowlisted command arrays
- Tool commands are policy-evaluated on canonicalized command/arg form

## Vision-First Computer-Use Boundary

- Vision-first desktop automation is feature-gated by `[computer_use]`.
- Default mode is `legacy_pilot`; `vision_enabled=false` keeps live vision execution off.
- Universal policy denies sensitive surfaces, blocked apps, low-confidence actions, and terminal control by default.
- Approval snapshots contain hashes, target geometry, expected effect, risk reasons, policy hash, and action hash; they do not contain raw screenshots.
- Windows live execution remains blocked with `WINDOWS_COMPUTER_USE_NOT_QUALIFIED` until signed qualification evidence exists.
## Vision-First Computer-Use Security Boundary

The Phase 2 vision-first runtime is fail-closed by default. Sensitive surfaces such as passwords, MFA, payment, wallet, private-key, system/security settings, legal-consent, and terminal/shell contexts are denied or stopped before OS input execution. Risky click/type/hotkey/file actions require approval and a fresh approval snapshot matching action hash, policy hash, active app/window, surface kind, and screenshot hash.

Windows and Linux live execution are not qualified. Windows must continue to report `WINDOWS_COMPUTER_USE_NOT_QUALIFIED`.

## Cross-Platform Computer-Use Gates

- macOS, Windows, and Linux share the same additive platform capability contract.
- `liveEnabled=true` requires a valid platform qualification report matching platform, commit, and config hash.
- Windows UAC secure desktop and Linux Wayland/X11 live input remain blocked until future signed evidence changes the gate.
- The public platform matrix fails if any profile appears live-ready without valid evidence.
- macOS live fixture qualification requires one-run opt-in, a human-readable
  acknowledgment, supervised-fixture-only scope, step approval, ready Screen
  Recording and Accessibility states, provider readiness, local fixture pass
  evidence, replay verification, and zero persisted raw screenshots. It is not
  unrestricted desktop automation and does not qualify Windows or Linux.
- Provider readiness is local-only and synthetic-fixture based. Missing models,
  invalid JSON, strict schema failures, and timeouts fail closed before any
  desktop capture or OS input path can run.
- Phase 4E additionally requires the configured model to be present locally and
  vision-capable. Capture/input backends refuse to run without one-run live
  opt-in, fixture-only scope, step approval, and non-missing manual macOS
  permission state.
