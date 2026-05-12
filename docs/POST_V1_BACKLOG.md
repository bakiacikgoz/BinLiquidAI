# Post-v1 Backlog

## Release Blockers For Hat B

Detailed operator handoff:
`docs/HAT_B_DESKTOP_RELEASE_HANDOFF_2026-05-10.md`.

Tracking issue: https://github.com/bakiacikgoz/BinLiquidAI/issues/4.

- Fix GitHub Actions account billing/spending limit so macOS release jobs can
  start. 2026-05-12 run `25751802651` failed before any workflow step and
  produced no preflight artifact because runners could not be allocated.
- Provision macOS signing and notarization credentials:
  `MACOS_SIGNING_IDENTITY`, `MACOS_SIGNING_CERT_P12_B64`,
  `MACOS_SIGNING_CERT_PASSWORD`, and either Apple notary API key secrets or
  Apple ID notarization secrets.
- Run `operator-panel-release-macos.yml` and capture codesign, notarytool,
  stapler, and clean-machine Gatekeeper evidence.
- Provision Windows signing credentials. `WINDOWS_TIMESTAMP_URL` is already
  configured on the `release-windows` environment.
- Run Windows signed RC, clean smoke, and promote workflows.
- Publish `windows-public-release-gate.json` with `status=pass`,
  `public_release_allowed=true`, and `blocking_reasons=[]`.

## Qualification Follow-Ups

- Run 24h release-candidate soak and publish signed evidence. **Completed
  2026-05-12:** run `rc24h-20260511T153314Z` completed successfully with
  signed qualification verification PASS and GA readiness green/go. Reporting
  alignment was fixed and aligned signed evidence was published with
  `24h_soak_flow=pass`.
  Use `scripts/run_qualification_soak_supervised.sh --detach --hours 24`
  so the soak is not tied to an interactive terminal session. Refresh the local
  enterprise identity assertion for more than 24 hours first if it has expired.
  2026-05-11: started as LaunchAgent from
  `/private/tmp/binliquid_soak_rc24h-20260511T153314Z` with run id
  `rc24h-20260511T153314Z`; expected completion is approximately
  `2026-05-12T15:34Z`.
- Run 72h final pre-GA soak if required by the release policy.
- Publish managed KMS/HSM live drill evidence.
- Complete non-developer operator validation.

## Computer-Use Follow-Ups

- Publish macOS supervised live qualification only after Screen Recording,
  Accessibility, local vision provider readiness, runtime summary, replay
  verification, and fresh qualification evidence all pass.
- Keep Windows and Linux live computer-use disabled until platform-specific
  qualification evidence exists.
- Do not market deterministic mock qualification as real-world desktop
  reliability evidence.

## Deferred Product Scope

- Multi-tenant control plane.
- Richer admin UI.
- Broader cloud-native integrations.
- Full PKCS#11/HSM breadth.
