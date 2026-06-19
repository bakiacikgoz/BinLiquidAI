# Enterprise Workspace Security Boundary

The enterprise workspace boundary is fail-closed. A request without a verified identity, active workspace membership, active enrollment, active device, and matching workspace binding must be denied.

## Non-Negotiable Defaults

- Raw enrollment tokens are shown once and never persisted.
- Snapshots must report `rawSecretsExposed=false`.
- The onboarding flow must not start a network listener by default.
- Cross-workspace memory reads are denied unless the principal has an active membership in the target workspace.
- External agents must be enrolled before external gateway requests are evaluated.

## Denial Conditions

The control plane denies when identity is disabled, workspace membership is missing, enrollment is pending or revoked, device status is not active, principal status is revoked, or an external agent record has no workspace binding.

## Operator Panel Surface

The Operator Panel exposes the enterprise workspace snapshot as read-only status: workspace setup, users and memberships, canonical roles, enrollment counts, fleet state, and identity health. It must not display raw tokens or any host secret material.

## Gate

Use the onboarding gate as the release check for this boundary:

```powershell
uv run python scripts/run_enterprise_workspace_onboarding_gate.py --profile enterprise --json
```
