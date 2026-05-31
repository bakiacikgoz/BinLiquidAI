# Agent Control Plane Claim Matrix

| Claim | Status | Required evidence | Current handling |
|---|---|---|---|
| Self-hosted Agent Control Plane | allowed/conditional | security baseline, signed qualification, GA readiness, signed evidence pack | Hat A control-plane gate |
| Public desktop app | blocked | signing, notarization, clean-machine smoke | Hat B blocked |
| Live computer-use macOS | conditional | supervised opt-in and platform qualification | gated execution surface |
| Live computer-use Windows/Linux | blocked | signed platform qualification | disabled by default |
| Multi-tenant SaaS | deferred | tenancy, network API, SSO/IAM and isolation evidence | out of scope |

Machine-readable evaluation is produced by
`scripts/evaluate_control_plane_claims.py`.
