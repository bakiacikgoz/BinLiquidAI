# Post-v1 Backlog

## Release Blockers For Hat B

- Provision macOS signing and notarization credentials:
  `MACOS_SIGNING_IDENTITY`, `MACOS_SIGNING_CERT_P12_B64`,
  `MACOS_SIGNING_CERT_PASSWORD`, and either Apple notary API key secrets or
  Apple ID notarization secrets.
- Run `operator-panel-release-macos.yml` and capture codesign, notarytool,
  stapler, and clean-machine Gatekeeper evidence.
- Provision Windows signing credentials and timestamp configuration.
- Run Windows signed RC, clean smoke, and promote workflows.
- Publish `windows-public-release-gate.json` with `status=pass`,
  `public_release_allowed=true`, and `blocking_reasons=[]`.

## Qualification Follow-Ups

- Run 24h release-candidate soak and publish signed evidence.
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
