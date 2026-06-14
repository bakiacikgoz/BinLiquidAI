# Design Partner RC Handoff

The RC handoff is allowed to move beyond Beta only when the Beta Operations
pack is ready and target-environment evidence is present. RC status must never
open claims that remain intentionally blocked.

## RC Preconditions

| Precondition | Ready Requirement | Failure Behavior |
|---|---|---|
| Beta Operations pack | `designPartnerBeta.status=ready` | `conditional` keeps RC conditional; `blocked` blocks RC. |
| Runtime truth | No silent fallback and no error data source | Blocking failure. |
| Preview boundary | Preview fixtures are not live evidence | Conditional until live/CLI evidence exists. |
| Provider governance | Native provider conformance is pass and provider policies are safe | Conditional when only credentials/target evidence are missing; blocking if policy unsafe. |
| Provider workflow proof | Read-only provider workflow has `executedMutations=0` and hash-only evidence | Blocking if mutations execute or raw evidence leaks. |
| Evidence index | At least one evidence pack is available | Conditional until target evidence exists. |
| Reports | At least one ready report is available | Conditional until target report exists. |
| Computer-use boundary | Surface remains `blocked` | Blocking failure if opened. |
| Public desktop boundary | Surface remains `blocked` | Blocking failure if opened. |
| Enterprise Hat A claim | Claim guard reports `allowed` | Conditional until evidence supports it. |
| Active alerts | No active error or critical alerts | Conditional until reviewed. |

## Target Evidence Checklist

Before an RC-ready claim:

- Generate a fresh control-plane snapshot from CLI or live bridge, not silent
  fixture fallback.
- Generate `artifacts/design-partner-beta/manifest.json` with `status=ready`.
- Generate `artifacts/design-partner-rc/design-partner-rc-status.json`.
- Verify evidence index and report artifacts under
  `artifacts/design-partner-rc/`.
- Keep claim guard matrix attached:
  `artifacts/design-partner-rc/claim-guard-matrix.json`.
- Keep external gateway smoke results attached:
  `artifacts/design-partner-rc/external_gateway_smoke.json`.

## Boundary Claims

RC can claim the self-hosted Agent Control Plane, governed runtime, Operator
Console visibility, approval lifecycle, evidence review, and External Agent
Gateway v1.1 policy behavior.

RC cannot claim:

- public desktop installer release readiness,
- unrestricted live computer-use,
- clean-machine desktop install success,
- multi-tenant SaaS control-plane readiness,
- irreversible external mutations without approval evidence.

## Gate Sequence

```bash
make design-partner-beta-gate
make design-partner-rc-gate
make design-partner-rc-audit-gate
make design-partner-handoff-gate
make pilot-readiness-gate
```

`make design-partner-rc-gate` is the strict release gate. It keeps release
semantics strict and may exit nonzero when RC remains `conditional`.
`make design-partner-rc-audit-gate` is the PR/audit gate: it exits zero only
when there are no blockers and every warning is in the expected conditional
allowlist.
`make design-partner-handoff-gate` builds and verifies the operator handoff
pack, release train manifest, first-run drill, claim boundary card, and Operator
Panel `Design Partner Handoff` route. It keeps public desktop release, live
computer-use, approval-free destructive mutation, and auto-release actions out
of scope.

## Handoff Pack

Use `docs/DESIGN_PARTNER_RC_HANDOFF_PACK.md`,
`docs/DESIGN_PARTNER_FIRST_RUN_OPERATIONS.md`,
`docs/MAINLINE_RC_RELEASE_TRAIN.md`,
`docs/DESIGN_PARTNER_SUPPORT_ESCALATION.md`, and
`docs/CLAIM_BOUNDARY_CARD_TEMPLATE.md` as the operator-facing handoff source.
The pack remains conditional until target evidence and independent attestation
are present, and it blocks on any false ready or unsupported claim.

## Rollback

If RC status overclaims readiness:

1. Revert the source change that opened the claim.
2. Regenerate the beta and RC artifacts from the previous known-good commit.
3. Confirm live computer-use and public desktop installer claims are still
   blocked.
4. Rerun `make design-partner-rc-gate`.
