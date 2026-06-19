# Enterprise Workspace PR Readiness

This runbook prepares the completed Enterprise Workspace Onboarding and Agent Enrollment branch for remote PR review. It does not add a runtime feature and does not perform push, PR, ready-for-review, merge, release, tag, or deployment actions.

## Local Gate

Run the Python gate directly:

```powershell
uv run python scripts/run_enterprise_workspace_pr_readiness_gate.py --profile enterprise --json
```

The gate writes:

```text
artifacts/enterprise-workspace-pr-readiness/pr_readiness_report.json
artifacts/enterprise-workspace-pr-readiness/pr_readiness_report.md
artifacts/enterprise-workspace-pr-readiness/pr_body_final.md
artifacts/enterprise-workspace-pr-readiness/remote_commands.md
artifacts/enterprise-workspace-pr-readiness/workflow_coverage.json
artifacts/enterprise-workspace-pr-readiness/mainline_rehearsal.json
```

On hosts with `make` available, the wrapper is:

```bash
make enterprise-workspace-pr-readiness-gate
```

Windows users can always use the Python command directly.

## What The Gate Verifies

- Current branch and clean working tree.
- Existing release closure report is present and has `status=pass`.
- Closure report hash is recorded for PR evidence.
- Closure report raw leak scan is `pass`.
- Full pytest, Operator Panel test/lint/build/e2e, and stable Tauri target-dir checks are present and passed in closure evidence.
- Remote CI workflow coverage includes the enterprise workspace release closure gate, stable Tauri target-dir validation, and artifact upload.
- Mainline rehearsal uses non-destructive git diff/log/merge-tree diagnostics.
- Generated PR body and remote command pack do not include high-confidence secret markers or destructive commands.

## Approval Boundary

The readiness gate always records:

```text
pushPerformed=false
prCreated=false
```

Push and draft PR creation require this exact separate approval:

```text
ONAY: Branch'i remote'a push et ve draft PR aç.
```

Ready-for-review and merge require separate explicit approvals. The generated `remote_commands.md` is a command pack only; it is not executed by the gate.

## Interpreting Tauri Diagnostics

The release closure gate treats Windows/OneDrive default Tauri target path failures as optional diagnostics. Required Tauri validation is:

```powershell
cargo test -q --manifest-path apps/operator-panel/src-tauri/Cargo.toml --target-dir apps/operator-panel/src-tauri/target-codex-test
```

The PR readiness gate verifies that this stable target-dir command passed in closure evidence and is represented in remote CI coverage.

## Mainline Rehearsal

The gate attempts `git fetch origin main --prune` and then uses local `origin/main` evidence for non-destructive comparison. If fetch is unavailable in a restricted local environment, the report carries a warning and still uses the local base ref when present.

## No-Ship Conditions

Do not push or open a PR while any of these remain:

- `pr_readiness_report.json` status is not `pass`.
- `noShipBlockers` is not empty.
- Workflow coverage is missing.
- Closure report is missing or not `pass`.
- Raw leak scan is not `pass`.
- Stable Tauri target-dir evidence is missing or failed.
- `remote_commands.md` includes destructive git or PR merge commands.
