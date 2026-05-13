# Hat A Closure Addendum - 2026-05-13

## Scope

This addendum closes the current Hat A source/CLI/enterprise self-hosted
evidence loop after the 24h soak and computer-use boundary refresh.

It does not publish or approve a Hat B desktop installer release. macOS and
Windows public desktop installer claims remain blocked by external signing,
notarization, signed-RC, clean-machine smoke, and promote-gate evidence.

## Evidence Added Since 2026-05-10

- 24h release-candidate soak run `rc24h-20260511T153314Z`: PASS.
- Signed aligned qualification evidence: PASS.
- GA readiness after 24h evidence: green/go.
- Computer-use deterministic boundary evidence: PASS.
- Internal unsigned Operator Panel no-bundle debug binaries:
  GitHub Actions run `25814422248` PASS for macOS `arm64`, macOS `x86_64`,
  and Windows `x64`.
- Managed KMS adapter live drill:
  `artifacts/readiness/2026-05-13/managed_kms_adapter_drill/` PASS for
  sign/verify, rotation dry-run, revoked key reject, restore-time historical
  artifact verification, and signed report verification.

## Supported Claims

- Hat A source/CLI/enterprise self-hosted candidate remains supported under the
  published constraints.
- Qualification and GA readiness evidence support the Hat A candidate boundary.
- Computer-use public live automation remains off by default and may only be
  claimed where fresh qualification evidence exists.

## Explicit Non-Claims

- No public macOS desktop installer release.
- No public Windows desktop installer release.
- No notarized macOS artifact claim.
- No Windows signed-RC, clean-VM, or promote-gate claim.
- No unrestricted live computer-use automation claim.
- No Windows or Linux live computer-use claim.
- No hardware HSM/PKCS#11 breadth claim.

## No-Ship Boundaries

- Internal unsigned desktop binaries are QA/evaluation artifacts only.
- Internal unsigned binaries must not be renamed or promoted as installers,
  signed release candidates, or public releases.
- Hat B remains blocked until `docs/HAT_B_DESKTOP_RELEASE_HANDOFF_2026-05-10.md`
  pass criteria are satisfied.

## Local Evidence

Expected local closure pack:

```text
artifacts/release-pack/0.4.1-hat-a-closure-2026-05-13/
```

Related evidence:

```text
artifacts/release-pack/0.4.1-hat-a-post-24h-2026-05-12/
artifacts/readiness/2026-05-13/operator_panel_internal_unsigned_25814422248/
artifacts/readiness/2026-05-13/managed_kms_adapter_drill/
```
