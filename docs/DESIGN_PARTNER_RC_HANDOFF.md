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
make pilot-readiness-gate
```

`make design-partner-rc-gate` may pass with an RC `conditional` status when
target-environment evidence is intentionally incomplete. It must fail only for
blocking safety or claim-boundary violations.

## Rollback

If RC status overclaims readiness:

1. Revert the source change that opened the claim.
2. Regenerate the beta and RC artifacts from the previous known-good commit.
3. Confirm live computer-use and public desktop installer claims are still
   blocked.
4. Rerun `make design-partner-rc-gate`.
