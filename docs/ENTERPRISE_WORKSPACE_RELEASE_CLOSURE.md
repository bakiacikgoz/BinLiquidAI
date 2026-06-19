# Enterprise Workspace Release Closure

This runbook closes the Enterprise Workspace Onboarding & Agent Enrollment v1 branch for PR review. It does not add a new runtime feature. It proves the branch is repeatable, cross-platform where practical, and safe to review.

## Primary Gate

Run the Python gate directly on every platform:

```powershell
uv run python scripts/run_enterprise_workspace_release_closure_gate.py --profile enterprise --json
```

The gate writes:

```text
artifacts/enterprise-workspace-release-closure/closure_report.json
artifacts/enterprise-workspace-release-closure/closure_report.md
artifacts/enterprise-workspace-release-closure/pr_body.md
```

On POSIX or CI hosts with `make` available, the wrapper is:

```bash
make enterprise-workspace-release-closure-gate
```

## What The Gate Checks

- Ruff for the full Python tree.
- Enterprise workspace and control-plane schema generation.
- Enterprise workspace onboarding gate.
- Pytest through `sys.executable -m pytest`, not a shell shim.
- Operator Panel test, lint, build, and enterprise workspace Playwright smoke.
- Tauri Rust tests with an explicit target directory.
- Raw token and high-confidence secret marker scan.
- `git diff --check`.

## Interpreting Results

`status=pass` means all required commands passed and the raw marker scan is clean.

`status=fail` means at least one required command failed or a raw marker was found. Do not push or open a PR until the blocker is resolved.

The default Tauri validation uses:

```powershell
cargo test -q --manifest-path apps/operator-panel/src-tauri/Cargo.toml --target-dir apps/operator-panel/src-tauri/target-codex-test
```

The explicit target directory avoids Tauri permission path misresolution seen under OneDrive and Unicode paths.

## PR Body

Use the generated `pr_body.md` as the first draft for the pull request. Confirm the validation block reflects the most recent local run before pushing.
