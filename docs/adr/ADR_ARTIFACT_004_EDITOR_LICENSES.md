# ADR_ARTIFACT_004: Editor Licenses

- Status: Accepted
- Owner: MAIN / Artifact Workspace
- Authoritative sources: approved artifact workspace plan sections 2.7, 12.11, 13 and Task 1.2; `docs/ARTIFACT_WORKSPACE_DEPENDENCY_MATRIX.md`
- Last verified: 2026-07-16 at Git commit `d1bb6c0097399064fc578976c466d2a8c693d482`
- Open decisions: purchase/entitlement records or accepted fallback ADRs for spreadsheet and canvas

## Context

Handsontable production use and tldraw production/offline use require entitlements that are not currently recorded. Evaluation modes are not acceptable production authority, and trial network contact conflicts with offline requirements.

## Decision

Licensed editors are fail-closed. `handsontable`, `@handsontable/react-wrapper`, and `tldraw` are deferred and their production capabilities remain forced off until a backend license doctor verifies an approved entitlement, permitted product/version scope, offline behavior, and build target.

License material is loaded only by the trusted backend/Tauri boundary from configured secret references. Literal keys, entitlement payloads, hashes that enable reuse, and vendor responses are never written to repository files, renderer state, logs, telemetry, audit bodies, or support bundles. The handshake exposes only enabled/disabled state and a stable reason code.

No evaluation key, silent fallback, environment-name heuristic, or client-side boolean can enable a licensed editor. Missing, invalid, expired, network-dependent, or unverifiable entitlement produces a disabled capability while archive/read/export-safe fallback behavior remains available. Candidate fallback choices require a separate accepted ADR before dependency installation.

## Consequences

- Spreadsheet and canvas editor implementation cannot begin merely because packages install.
- Production builds remain usable through legacy/read-only or later accepted community fallbacks.
- CI checks package presence, capability resolution, redaction, and forced-off behavior without secrets.
- License acquisition is an external release dependency, not a code defect.

## Rejected alternatives

- `non-commercial-and-evaluation` in production: rejected by license terms.
- tldraw trial mode: rejected because it is not offline-compatible production proof.
- Renderer-entered license keys: rejected as a secret and authority boundary violation.
