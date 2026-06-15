# Mainline Integration Runbook

Use this runbook when moving Design Partner Beta or RC readiness work into
`main`.

## Branch Rules

- Do not commit directly on `main` when the worktree is dirty.
- Create or use a feature branch from the current `main` head.
- Push the feature branch before opening or updating a PR.
- Do not force push `main`.

## Local Checks

Run the relevant gate before requesting merge:

```bash
FALLOW_GATE_MODE=enforce make operator-panel-fallow-gate
make design-partner-beta-gate
make design-partner-rc-gate
make design-partner-handoff-gate
make pilot-readiness-gate
make mainline-gate
git diff --check
```

For a Beta-only branch, `design-partner-rc-gate` may remain conditional if the RC
evidence closure is intentionally not part of the branch. For RC closure work,
`design-partner-rc-gate` must pass with `status=pass` and no warnings.
For design partner RC handoff work, `design-partner-handoff-gate` is the
operator handoff readiness gate. It may pass with an intentionally conditional
handoff when target-environment evidence is absent, but it must block on claim
overreach, leaked raw material, secret markers, hash mismatches, or false ready
claims.

## PR Path

```bash
git push -u origin <branch>
gh pr create --base main --head <branch> --title "<title>" --body "<summary>"
gh pr checks --watch
gh pr merge --merge --delete-branch=false
git switch main
git pull --ff-only origin main
make mainline-gate
```

Before any Design Partner RC discussion, generate and verify the release decision dossier:

```bash
uv run python scripts/run_rc_release_decision_gate.py --profile enterprise --json
```

This gate is local and non-destructive. It does not merge, tag, publish, deploy, or impersonate human sign-off.

Merge only after local gates and remote checks pass.

## Direct Merge Fallback

Use this only when a PR is not available and branch protection allows it:

```bash
git switch main
git pull --ff-only origin main
git merge --no-ff <branch> -m "Merge <branch>"
make mainline-gate
git push origin main
```

## Rollback

If `main` breaks after merge, prefer a revert commit:

```bash
git switch main
git pull --ff-only origin main
git revert <merge_commit_sha>
git push origin main
```

Never use force push as a rollback path.
