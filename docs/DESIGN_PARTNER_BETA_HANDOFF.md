# Design Partner Beta Handoff

This handoff describes what can be shown to a design partner when the Beta
Operations pack reports `ready`. It is an evidence closure document, not a new
product-scope expansion.

## Supported Claims

| Claim | Status | Evidence |
|---|---|---|
| Self-hosted Agent Control Plane | Supported | `artifacts/design-partner-pilot/manifest.json` |
| Policy and approval gated agent runs | Supported | `artifacts/design-partner-pilot/pilot_metrics.json` |
| External Agent Gateway v1.1 read and governed write handoff | Supported | `artifacts/external-agent-v1-1/results.json` |
| Fallow code intelligence rollout gate | Supported | `artifacts/code-intelligence/fallow/summary.json` |
| Local-only pilot feedback bundle | Supported | `artifacts/pilot-ops/pilot_feedback_bundle.json` |
| Live computer-use execution | Blocked | Qualification evidence is not in this beta scope. |
| Public desktop installer release | Blocked | Signing, notarization, and clean-machine evidence are Hat B scope. |

## Demo Flow

1. Dashboard: confirm control-plane status, claim boundaries, and Beta
   Operations readiness.
2. Agents: show registered agents and risk profile boundaries.
3. Policy: simulate decisions before execution.
4. Runs: inspect run status, approvals, replay, and artifacts.
5. Approvals: keep external writes approval-gated.
6. Evidence: verify hash, signature, replay, and redaction status.
7. Reports: review readiness and evidence reports.
8. Operations: run qualification, support, security, and key workflows.
9. Execution Surfaces: confirm live computer-use and public desktop installer
   remain blocked.

## Fallow Closure

The Fallow report keeps legacy dead-code, duplication, and health buckets
visible as baseline debt. Beta readiness is based on the `rollout_gate`
new-only audit:

- `rollout_gate.status=pass`
- `warnings=[]`
- `blocking_reasons=[]`
- `boundaries.total=0`
- `secret_scan.status=pass`
- `telemetry_disabled=true`

New feature PRs must not add Fallow rollout debt. Existing baseline debt is not
hidden; it is surfaced in the Operator Panel Beta Operations card and in
`baseline_warnings`.

## External Agent Gateway v1.1 Partner Checklist

Partner agents must satisfy the v1.1 contract before pilot use:

- Read-only inspector actions may be allowed.
- External write actions require approval.
- Destructive actions are denied.
- Duplicate idempotency keys return stable replay behavior.
- Replay mismatch and idempotency conflicts are rejected.
- Payloads remain redacted and local evidence paths stay bounded.

Current result summary:

- `read_only_inspector`: pass
- `approval_required_writer`: pass
- `destructive_denied_agent`: pass
- `idempotent_replay`: pass
- `idempotency_conflict`: pass
- `replay_verify`: pass

## Local-only Feedback Boundary

`PILOT_FEEDBACK.md` and `pilot_feedback_bundle.json` are local-only handoff
artifacts. They must not include PII, raw screenshots, private keys, API
tokens, or personal contact/payment identifiers. Operator notes can be shared
only after explicit review.

## Required Local Gates

```bash
FALLOW_GATE_MODE=enforce make operator-panel-fallow-gate
make ci-node24-inventory
make external-agent-v1-1-gate
make pilot-operations-gate
make design-partner-beta-gate
```

## No-ship Conditions

- Beta manifest is `conditional` or `blocked`.
- Fallow rollout warnings are present while a ready claim is made.
- Secret scan or boundary checks fail.
- Public desktop installer is shown as allowed.
- Live computer-use is shown as allowed without qualification evidence.
- Preview fixtures are described as live customer evidence.
