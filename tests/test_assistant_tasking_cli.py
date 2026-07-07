from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from binliquid.cli import app
from binliquid.control_plane.registry import AgentRegistry, load_agent_spec
from tests.test_external_agent_gateway_v1_1 import _bind_enrollment

REPO_ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def test_assistant_tasking_cli_plan_submit_status_explain(tmp_path: Path) -> None:
    root_dir = tmp_path / "cp"
    registry = AgentRegistry(root_dir=root_dir)
    registry.register(
        load_agent_spec(REPO_ROOT / "examples/control_plane/agent_external_gateway.yaml"),
        actor="test",
    )
    _bind_enrollment(registry=registry, root_dir=root_dir)

    plan = runner.invoke(
        app,
        [
            "assistant",
            "task",
            "plan",
            "--message",
            "Governed ops agent'e son servis uyarilarini incele.",
            "--root-dir",
            str(root_dir),
            "--json",
        ],
    )
    assert plan.exit_code == 0, plan.stdout
    plan_payload = json.loads(plan.stdout)
    assert plan_payload["status"] == "planned"
    assert plan_payload["safeToSubmit"] is True

    submit = runner.invoke(
        app,
        [
            "assistant",
            "task",
            "submit",
            "--proposal-id",
            plan_payload["proposalId"],
            "--confirm-plan-hash",
            plan_payload["planHash"],
            "--operator-id",
            "operator-local",
            "--root-dir",
            str(root_dir),
            "--json",
        ],
    )
    assert submit.exit_code == 0, submit.stdout
    assert json.loads(submit.stdout)["status"] == "accepted"

    status = runner.invoke(
        app,
        ["assistant", "task", "status", "--proposal-id", plan_payload["proposalId"], "--json"],
    )
    assert status.exit_code == 0, status.stdout
    assert json.loads(status.stdout)["evidenceRefs"]

    explain = runner.invoke(
        app,
        ["assistant", "task", "explain", "--proposal-id", plan_payload["proposalId"], "--json"],
    )
    assert explain.exit_code == 0, explain.stdout
    assert "docs/ASSISTANT_GOVERNED_TASKING.md" in json.loads(explain.stdout)["sources"]


def test_assistant_tasking_cli_rejects_hash_mismatch(tmp_path: Path) -> None:
    root_dir = tmp_path / "cp"
    plan = runner.invoke(
        app,
        [
            "assistant",
            "task",
            "plan",
            "--message",
            "External agent eski kayitlari silsin.",
            "--root-dir",
            str(root_dir),
            "--json",
        ],
    )
    payload = json.loads(plan.stdout)
    submit = runner.invoke(
        app,
        [
            "assistant",
            "task",
            "submit",
            "--proposal-id",
            payload["proposalId"],
            "--confirm-plan-hash",
            "sha256:" + "0" * 64,
            "--operator-id",
            "operator-local",
            "--root-dir",
            str(root_dir),
            "--json",
        ],
    )
    assert submit.exit_code == 3
    assert json.loads(submit.stdout)["reasonCode"] == "ASSISTANT_TASK_PLAN_HASH_MISMATCH"
