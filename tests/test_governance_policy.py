from __future__ import annotations

from pathlib import Path

from binliquid.governance.models import GovernanceAction
from binliquid.governance.policy import evaluate_task, evaluate_tool, load_policy, normalize_command


def test_default_policy_requires_approval_for_code_tasks() -> None:
    bundle = load_policy(Path("config/policies/default.toml"))
    match = evaluate_task(bundle.policy, task_type="code")

    assert match.action == GovernanceAction.REQUIRE_APPROVAL
    assert match.reason_code == "POLICY_REQUIRE_APPROVAL"


def test_tool_policy_blocks_destructive_python_args() -> None:
    bundle = load_policy(Path("config/policies/default.toml"))
    match = evaluate_tool(
        bundle.policy,
        command_root="python",
        args=["-c", "import os; os.remove('tmp.txt')"],
    )

    assert match.action == GovernanceAction.DENY
    assert match.reason_code == "POLICY_DENY"


def test_normalize_command_resolves_paths_against_workdir(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    root, args = normalize_command(["python", "../outside.txt", "./inside.txt"], workdir=workspace)

    assert root == "python"
    assert args[0].endswith("outside.txt")
    assert args[1] == "./inside.txt"
