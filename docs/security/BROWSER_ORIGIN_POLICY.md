# Browser Origin Policy

This policy is enforced per browser mode. There is no global allow-origin
switch and a decision in one mode never grants access in another mode.

## User browser

- An address explicitly submitted through the user browser may use `https`.
- `http`, `file`, `javascript`, `data`, `tauri`, and `asset` are denied.
- Every navigation, including a redirect, is checked again against this rule.

## Preview browser

- A preview may use only an exact `localhost` or `127.0.0.1` origin that the
  trusted ImperaOS runtime registered with an explicit port.
- The renderer cannot register preview origins. Arbitrary local ports are
  denied, as are host, scheme, or port substitutions during redirects.

## Agent browser

- An agent session requires both a task ID and a domain from that task's
  trusted task/deployment allowlist.
- It may use only `https` to an exact allowed domain. Missing or empty policy
  fails closed.
- Each agent window has a fresh browser profile; it cannot read user browser
  cookies or reuse the user session.

## External effects

- Redirects are rechecked under their session's mode policy.
- New windows are denied until the user explicitly approves reopening the URL
  in a governed browser session.
- Downloads and external application schemes remain blocked after notifying
  the user. They require a future governed save/approval workflow; an
  acknowledgement is not an approval to execute.

## Enforcement

The policy and its runtime registries live in
`apps/operator-panel/src-tauri/src/browser.rs`. Browser windows have separate
data directories by mode. The default Tauri capability applies only to the
`main` window, so remote child webviews do not receive renderer IPC
permissions.
