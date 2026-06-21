# Enterprise Workspace Remote PR CI Closure

This runbook closes the Enterprise Workspace remote PR and CI evidence loop without
performing a merge.

## Scope

- Collect local release closure and PR readiness evidence.
- Collect PR metadata and GitHub Actions or PR check status when available.
- Reconcile local evidence SHA, PR head SHA, required CI checks, branch state, and
  no-ship blockers.
- Write evidence to `artifacts/enterprise-workspace-remote-pr-ci/`.
- Keep `mergePerformed=false`.

## Local command

```bash
uv run python scripts/run_enterprise_workspace_remote_pr_ci_gate.py \
  --profile enterprise \
  --branch codex/enterprise-workspace-onboarding-agent-enrollment-v1 \
  --base main \
  --json
```

If PR metadata or CI checks are unavailable, the report is `conditional` or
`blocked` and `merge_readiness.md` remains not ready.

## Approval boundary

Remote mutation requires this exact approval text:

```text
ONAY: Branch'i remote'a push et ve draft PR aç.
```

The gate always writes `post_pr_commands.md` with the push, draft PR, and CI
inspection commands. The command pack intentionally omits force push and PR merge
commands.

## Outputs

- `remote_pr_ci_report.json`
- `remote_pr_ci_report.md`
- `ci_checks.json`
- `pr_metadata.json` when PR metadata exists
- `merge_readiness.md`
- `post_pr_commands.md`

## No-Ship blockers

- Dirty worktree
- Wrong branch
- Local release closure or PR readiness failure
- Local evidence SHA mismatch
- PR head SHA mismatch
- Required CI failure, skipped required CI, or required CI pending
- Raw leak or unsupported claim in PR body evidence
- Any attempted merge, which must remain false in this gate

## Merge readiness

Merge readiness is true only when local evidence passes, PR metadata exists, the PR
head SHA matches local HEAD, all required CI checks pass, no no-ship blockers
remain, and `mergePerformed=false`.
