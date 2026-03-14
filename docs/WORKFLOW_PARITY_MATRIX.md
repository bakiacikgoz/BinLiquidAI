# Workflow Parity Matrix

## `v0.6` Operator Workflow Parity

| Operator workflow | UI surface | Core source of truth |
| --- | --- | --- |
| Submit governed task run | `Tasks` workspace | `team run --job-id` |
| Monitor active run | `Runs > Overview / Stream` | `status.json`, `events.jsonl` |
| Review pending approvals | `Approvals` workspace | `approval pending/show` |
| Approve / reject / execute | `Approvals` workspace | `approval decide/execute` |
| Inspect replay | `Runs > Replay` | `team replay --json` |
| Export artifacts | `Runs` and rail actions | `team artifacts --export` |
| Resume blocked run | `Tasks` / right rail | `team resume --resume-job-id` |
| Verify doctor and config | `System` workspace | `doctor`, `config resolve`, `operator capabilities` |

## `v0.7` Enterprise Operations Parity

| Operator workflow | UI surface | Core source of truth |
| --- | --- | --- |
| Identity and permission check | `Operations > Identity` | `auth whoami/check` |
| Qualification and readiness | `Operations > Qualification` | `qualification run`, `metrics snapshot`, `ga readiness` |
| Security baseline | `Operations > Security` | `security baseline` |
| Key status and verification | `Operations > Keys` | `keys status/verify/rotate-plan` |
| Support bundle export | `Operations > Support` | `support bundle export` |
| Backup / restore verification | `Operations > Backup / Restore / Migrate` | `backup create/verify`, `restore verify` |
| Migration planning | `Operations > Backup / Restore / Migrate` | `migrate plan`, `migrate apply --dry-run` |

## `v0.8-pilot` Computer Use

| Pilot task family | Mode | Approval posture | Evidence |
| --- | --- | --- | --- |
| Allowlisted page inspection | `dry_run`, `step_approval` | step approval by default | redacted |
| Bounded form-fill draft | `step_approval` | required | redacted |
| Low-risk queue/status update | `step_approval` | required | redacted |
