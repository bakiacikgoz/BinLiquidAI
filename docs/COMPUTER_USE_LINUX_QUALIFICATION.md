# Linux Computer-Use Qualification

Status: scaffolded, not qualified

Linux live computer-use automation remains disabled with
`LINUX_COMPUTER_USE_NOT_QUALIFIED`.

## Current Gate Behavior

- Wayland sessions report `LINUX_WAYLAND_NOT_QUALIFIED`.
- X11 sessions report `LINUX_X11_NOT_QUALIFIED`.
- Missing session metadata reports `LINUX_SESSION_NOT_DETECTED`.
- Capture and input backends default to `disabled`.
- Mock backends do not permit live execution without a matching platform qualification report.

## Required Evidence Before Enablement

- A safe screen observation backend for the target compositor.
- A safe input backend with explicit session and focus guards.
- Sensitive-surface deny tests for password, MFA, payment, key, security, and terminal contexts.
- Replay integrity evidence for every mutating step.
- Fresh approval snapshot enforcement.
- Raw screenshot persistence count of `0` by default.
- Clean VM or clean desktop-session smoke evidence.

## Product Claim Rule

The product must keep reporting `LINUX_COMPUTER_USE_NOT_QUALIFIED` until a future release
adds signed Linux qualification evidence and a separate gate changes the operator contract.
