# Hat A Candidate Release Notes - 2026-05-10

## Scope

This release note covers Hat A only: source, CLI, Team Runtime, enterprise
self-hosted readiness, qualification evidence, and computer-use safety
boundaries.

This is not a Hat B desktop installer release. macOS notarized artifacts and
Windows public installer artifacts remain blocked until external signing,
notarization, signed RC, and clean-machine smoke evidence are available.

## Evidence Summary

- Mainline gate: PASS.
- Team Runtime pilot gate: PASS.
- Enterprise gate: PASS.
- 6h qualification run: PASS.
- Qualification report: `qualification_status=pass`,
  `recommended_status=green`, `go_no_go=go`.
- GA readiness after qualification: `overall_status=green`, `go_no_go=go`.
- Qualification and GA readiness signatures: verified.
- Computer-use platform matrix: PASS for fail-closed safety boundaries.

## Supported

- Core CLI/runtime under the documented local-first envelope.
- Team Runtime under bounded, governed, restricted/enterprise workflows.
- Enterprise self-hosted profile with local-file asymmetric signing evidence.
- Hat A candidate release claims backed by signed 6h qualification evidence.

## Conditional

- Enterprise bounded-concurrency, approval-heavy, and conflict-heavy workflows
  remain constrained to the published support table in the qualification report.
- Operator Panel is build/test validated locally, but desktop installer release
  claims require Hat B signing and clean-machine evidence.

## Not Supported / No Claim

- Public macOS desktop installer release.
- Public Windows desktop installer release.
- Live cross-platform computer-use automation.
- Windows and Linux live computer-use.
- macOS supervised live computer-use without fresh provider, runtime summary,
  replay verification, permissions, and qualification evidence.
- High-concurrency general multi-agent execution beyond bounded support.

## Residual Risks

- 24h soak evidence not yet published.
- Managed KMS live drill not yet published.
- Non-developer operator validation not yet published.
- Desktop signing/notarization credentials not configured.

## Evidence Pack

The local evidence pack is written under:

```text
artifacts/release-pack/0.4.1-hat-a-2026-05-10/
```

GitHub draft/prerelease metadata:

- Tag: `hat-a-v0.4.1-2026-05-10`.
- Title: `Hat A Candidate v0.4.1 - 2026-05-10`.
- Evidence archive SHA256:
  `a0d0db298316ccc487212a0ceb9b8d3af38b037a479e402d3085c5b85ff59cc3`.
- Assets uploaded: evidence pack `.tar.gz` and matching `.sha256` file.
- Release remains draft/prerelease and is not marked latest.

Do not tag or publish a Hat B desktop release until the blocked desktop gates are
green.
