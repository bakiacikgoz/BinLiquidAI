from __future__ import annotations

import json
from pathlib import Path

from scripts import run_enterprise_workspace_pr_readiness_gate as gate

HEAD = "b" * 40
CLOSURE_HEAD = "a" * 40


def _write_closure(
    root: Path,
    *,
    status: str = "pass",
    head: str = HEAD,
    raw_status: str = "pass",
) -> None:
    closure_root = root / "closure"
    closure_root.mkdir(parents=True)
    (closure_root / "pr_body.md").write_text("## Summary\n- Existing PR body.\n", encoding="utf-8")
    payload = {
        "schemaVersion": "enterprise-workspace.release-closure/v1",
        "status": status,
        "headSha": head,
        "rawLeakScan": {
            "status": raw_status,
            "findings": [] if raw_status == "pass" else [{"path": "x"}],
        },
        "tauri": {"status": "pass"},
        "commandResults": [
            {"name": "pytest_full", "status": "pass"},
            {"name": "operator_panel_test", "status": "pass"},
            {"name": "operator_panel_lint", "status": "pass"},
            {"name": "operator_panel_build", "status": "pass"},
            {"name": "enterprise_workspace_e2e", "status": "pass"},
            {"name": "tauri_cargo_test_stable_target", "status": "pass"},
        ],
    }
    (closure_root / "closure_report.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def _write_workflow(root: Path) -> None:
    workflow_root = root / ".github" / "workflows"
    workflow_root.mkdir(parents=True)
    (workflow_root / "enterprise-workspace-release-closure.yml").write_text(
        "steps:\n"
        "  - run: uv run python "
        "scripts/run_enterprise_workspace_release_closure_gate.py "
        "--profile enterprise --json\n"
        "  - run: cargo test -q "
        "--manifest-path apps/operator-panel/src-tauri/Cargo.toml "
        "--target-dir apps/operator-panel/src-tauri/target-codex-test\n"
        "  - uses: actions/upload-artifact@v4\n",
        encoding="utf-8",
    )


def _patch_git(monkeypatch, *, status: str = "", head: str = HEAD, diff: str = "") -> None:
    def fake_git_text(args: list[str], *, repo_root: Path = gate.REPO_ROOT) -> str:
        if args == ["branch", "--show-current"]:
            return gate.DEFAULT_EXPECTED_BRANCH
        if args == ["rev-parse", "HEAD"]:
            return head
        if args == ["status", "--short"]:
            return status
        if args[:2] == ["rev-list", "--count"]:
            return "1"
        return ""

    def fake_run_git(
        args: list[str],
        *,
        repo_root: Path = gate.REPO_ROOT,
        timeout: int = 60,
    ):
        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        result = Result()
        if args[:2] == ["diff", "--name-only"]:
            result.stdout = diff
        if args[:2] == ["rev-parse", "--verify"]:
            result.stdout = "base"
        if args and args[0] == "merge-tree":
            result.stdout = "merged"
        return result

    monkeypatch.setattr(gate, "_git_text", fake_git_text)
    monkeypatch.setattr(gate, "_run_git", fake_run_git)


def test_pr_readiness_pass_writes_artifacts(tmp_path: Path, monkeypatch) -> None:
    _write_closure(tmp_path)
    _write_workflow(tmp_path)
    _patch_git(monkeypatch)

    report = gate.run_enterprise_workspace_pr_readiness_gate(
        profile="enterprise",
        closure_root=tmp_path / "closure",
        output_root=tmp_path / "out",
        expected_branch=gate.DEFAULT_EXPECTED_BRANCH,
        base_ref="origin/main",
        repo_root=tmp_path,
        fetch_main=False,
    )

    assert report.status == "pass"
    assert report.push_performed is False
    assert report.pr_created is False
    assert report.workflow_coverage.status == "pass"
    assert (tmp_path / "out" / "pr_readiness_report.json").exists()
    assert (tmp_path / "out" / "pr_readiness_report.md").exists()
    assert (tmp_path / "out" / "pr_body_final.md").exists()
    assert (tmp_path / "out" / "remote_commands.md").exists()


def test_missing_closure_report_blocks(tmp_path: Path, monkeypatch) -> None:
    _write_workflow(tmp_path)
    _patch_git(monkeypatch)

    report = gate.run_enterprise_workspace_pr_readiness_gate(
        profile="enterprise",
        closure_root=tmp_path / "missing",
        output_root=tmp_path / "out",
        expected_branch=gate.DEFAULT_EXPECTED_BRANCH,
        base_ref="origin/main",
        repo_root=tmp_path,
        fetch_main=False,
    )

    assert report.status == "blocked"
    assert "CLOSURE_REPORT_MISSING" in report.no_ship_blockers


def test_closure_status_fail_blocks(tmp_path: Path, monkeypatch) -> None:
    _write_closure(tmp_path, status="fail")
    _write_workflow(tmp_path)
    _patch_git(monkeypatch)

    report = gate.run_enterprise_workspace_pr_readiness_gate(
        profile="enterprise",
        closure_root=tmp_path / "closure",
        output_root=tmp_path / "out",
        expected_branch=gate.DEFAULT_EXPECTED_BRANCH,
        base_ref="origin/main",
        repo_root=tmp_path,
        fetch_main=False,
    )

    assert report.status == "blocked"
    assert "CLOSURE_STATUS_NOT_PASS" in report.no_ship_blockers


def test_dirty_tree_blocks(tmp_path: Path, monkeypatch) -> None:
    _write_closure(tmp_path)
    _write_workflow(tmp_path)
    _patch_git(monkeypatch, status=" M scripts/example.py")

    report = gate.run_enterprise_workspace_pr_readiness_gate(
        profile="enterprise",
        closure_root=tmp_path / "closure",
        output_root=tmp_path / "out",
        expected_branch=gate.DEFAULT_EXPECTED_BRANCH,
        base_ref="origin/main",
        repo_root=tmp_path,
        fetch_main=False,
    )

    assert report.status == "blocked"
    assert "DIRTY_WORKTREE" in report.no_ship_blockers


def test_head_mismatch_warns_for_readiness_commit(tmp_path: Path, monkeypatch) -> None:
    _write_closure(tmp_path, head=CLOSURE_HEAD)
    _write_workflow(tmp_path)
    _patch_git(
        monkeypatch,
        head=HEAD,
        diff="scripts/run_enterprise_workspace_pr_readiness_gate.py\n"
        "tests/test_enterprise_workspace_pr_readiness_gate.py\n"
        "docs/ENTERPRISE_WORKSPACE_PR_READINESS.md\n"
        ".github/workflows/enterprise-workspace-release-closure.yml\n"
        "Makefile\n",
    )

    report = gate.run_enterprise_workspace_pr_readiness_gate(
        profile="enterprise",
        closure_root=tmp_path / "closure",
        output_root=tmp_path / "out",
        expected_branch=gate.DEFAULT_EXPECTED_BRANCH,
        base_ref="origin/main",
        repo_root=tmp_path,
        fetch_main=False,
    )

    assert report.status == "pass"
    assert report.warnings


def test_raw_leak_scan_fail_blocks(tmp_path: Path, monkeypatch) -> None:
    _write_closure(tmp_path, raw_status="fail")
    _write_workflow(tmp_path)
    _patch_git(monkeypatch)

    report = gate.run_enterprise_workspace_pr_readiness_gate(
        profile="enterprise",
        closure_root=tmp_path / "closure",
        output_root=tmp_path / "out",
        expected_branch=gate.DEFAULT_EXPECTED_BRANCH,
        base_ref="origin/main",
        repo_root=tmp_path,
        fetch_main=False,
    )

    assert report.status == "blocked"
    assert "CLOSURE_RAW_SCAN_FAIL" in report.no_ship_blockers


def test_workflow_missing_blocks_remote_ready(tmp_path: Path, monkeypatch) -> None:
    _write_closure(tmp_path)
    _patch_git(monkeypatch)

    report = gate.run_enterprise_workspace_pr_readiness_gate(
        profile="enterprise",
        closure_root=tmp_path / "closure",
        output_root=tmp_path / "out",
        expected_branch=gate.DEFAULT_EXPECTED_BRANCH,
        base_ref="origin/main",
        repo_root=tmp_path,
        fetch_main=False,
    )

    assert report.status == "blocked"
    assert "WORKFLOW_COVERAGE_MISSING" in report.no_ship_blockers


def test_remote_commands_no_force_or_merge(tmp_path: Path) -> None:
    output = tmp_path / "remote_commands.md"

    text = gate.build_remote_commands(
        branch=gate.DEFAULT_EXPECTED_BRANCH,
        base_branch="main",
        pr_body_path=tmp_path / "pr_body_final.md",
        output_path=output,
    )

    assert "git push -u origin" in text
    assert "gh pr create" in text
    for forbidden in gate.REMOTE_COMMAND_FORBIDDEN:
        assert forbidden not in text


def test_pr_body_final_contains_optional_tauri_note(tmp_path: Path, monkeypatch) -> None:
    _write_closure(tmp_path)
    _write_workflow(tmp_path)
    _patch_git(monkeypatch)
    report = gate.run_enterprise_workspace_pr_readiness_gate(
        profile="enterprise",
        closure_root=tmp_path / "closure",
        output_root=tmp_path / "out",
        expected_branch=gate.DEFAULT_EXPECTED_BRANCH,
        base_ref="origin/main",
        repo_root=tmp_path,
        fetch_main=False,
    )

    body = (tmp_path / "out" / "pr_body_final.md").read_text(encoding="utf-8")

    assert report.status == "pass"
    assert "Optional Environment Diagnostic" in body
    assert "target-codex-test" in body


def test_dedicated_workflow_runs_closure_gate_and_uploads_artifacts() -> None:
    workflow = Path(".github/workflows/enterprise-workspace-release-closure.yml")

    text = workflow.read_text(encoding="utf-8")

    assert "scripts/run_enterprise_workspace_release_closure_gate.py" in text
    assert "actions/upload-artifact@v4" in text
    assert "target-codex-test" in text
