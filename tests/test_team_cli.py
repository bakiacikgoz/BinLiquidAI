from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from binliquid.cli import app
from binliquid.governance.runtime import GovernanceRuntime
from binliquid.runtime.config import RuntimeConfig
from binliquid.schemas.models import OrchestratorResult

runner = CliRunner()


class FakeTeamOrchestrator:
    governance_runtime = None
    _memory_manager = None

    def process(
        self,
        user_input: str,
        session_context: dict[str, str] | None = None,
        use_router: bool = True,
    ) -> OrchestratorResult:
        del user_input, session_context, use_router
        return OrchestratorResult(
            final_text="team-ok",
            used_path="llm_only",
            fallback_events=[],
            trace_id="trace-team",
            metrics={"router_reason_code": "RULE_ROUTE"},
        )


class ApprovalAwareFakeTeamOrchestrator:
    def __init__(self, runtime: GovernanceRuntime):
        self.governance_runtime = runtime
        self._memory_manager = None
        self._counter = 0

    def process(
        self,
        user_input: str,
        session_context: dict[str, str] | None = None,
        use_router: bool = True,
    ) -> OrchestratorResult:
        del use_router
        session_context = session_context or {}
        run_id = str(session_context.get("job_id") or "job-test")
        override_id = session_context.get("governance_approval_id")
        decision, ticket = self.governance_runtime.evaluate_task(
            run_id=run_id,
            task_type="chat",
            user_input=user_input,
            override_approval_id=override_id,
        )
        self._counter += 1
        if decision.action.value == "require_approval":
            return OrchestratorResult(
                final_text="approval-required",
                used_path="governance_pending",
                fallback_events=["approval_pending"],
                trace_id=f"trace-{self._counter}",
                metrics={
                    "governance_reason_code": decision.reason_code,
                    "approval_id": ticket.approval_id if ticket else None,
                },
            )
        if decision.action.value == "deny":
            return OrchestratorResult(
                final_text="blocked",
                used_path="governance_blocked",
                fallback_events=["governance_blocked"],
                trace_id=f"trace-{self._counter}",
                metrics={"governance_reason_code": decision.reason_code},
            )
        return OrchestratorResult(
            final_text="team-ok-after-resume",
            used_path="llm_only",
            fallback_events=[],
            trace_id=f"trace-{self._counter}",
            metrics={"router_reason_code": "RULE_ROUTE"},
        )


def _write_spec(path: Path) -> None:
    payload = {
        "version": "1",
        "team": {
            "team_id": "team-test",
            "supervisor_policy": "sequential_then_parallel",
            "agents": [
                {
                    "agent_id": "agent-intake",
                    "role": "Intake Agent",
                    "allowed_task_types": ["chat", "plan"],
                    "profile_name": "balanced",
                    "model_overrides": {},
                    "memory_scope_access": ["session", "case"],
                    "tool_policy_profile": "default",
                    "approval_mode": "auto",
                }
            ],
            "handoff_rules": [],
            "termination_rules": {
                "max_tasks": 8,
                "max_retries": 1,
                "max_handoff_depth": 8,
            },
        },
        "tasks": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_task_approval_policy(path: Path) -> None:
    payload = """
policy_schema_version = "1.0"
policy_version = "team-task-approval"
web_egress = "deny"

[[task_rules]]
id = "task-chat-approval"
task_types = ["chat"]
action = "require_approval"

[[tool_rules]]
id = "tool-python"
command_roots = ["python", "uv", "pytest", "ruff", "rg"]
action = "allow"
arg_deny_regex = []

[[handoff_rules]]
id = "handoff-allow"
from_roles = []
to_roles = []
action = "allow"

[[memory_scope_rules]]
id = "memory-allow"
scopes = ["session", "team", "case"]
producer_roles = []
visibilities = ["private", "team", "case"]
action = "allow"

[pii_rules]
patterns = []
"""
    path.write_text(payload, encoding="utf-8")


def test_team_validate_and_run(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    spec_path = tmp_path / "team.json"
    _write_spec(spec_path)

    monkeypatch.setattr(
        "binliquid.cli._build_orchestrator",
        lambda *a, **k: FakeTeamOrchestrator(),
    )

    validate = runner.invoke(app, ["team", "validate", "--spec", str(spec_path), "--json"])
    assert validate.exit_code == 0
    assert '"status": "ok"' in validate.stdout

    run = runner.invoke(
        app,
        [
            "team",
            "run",
            "--spec",
            str(spec_path),
            "--once",
            "short request",
            "--json",
        ],
    )
    assert run.exit_code == 0
    payload = json.loads(run.stdout)
    assert payload["job"]["status"] == "completed"
    checkpoint_db = tmp_path / ".binliquid" / "team" / "checkpoints.sqlite3"
    assert checkpoint_db.exists()
    with sqlite3.connect(checkpoint_db) as conn:
        row = conn.execute(
            "SELECT status FROM team_checkpoints WHERE job_id = ?",
            (payload["job"]["job_id"],),
        ).fetchone()
    assert row is not None
    assert row[0] == "completed"

    status = runner.invoke(app, ["team", "status", "--job-id", payload["job"]["job_id"], "--json"])
    assert status.exit_code == 0
    status_payload = json.loads(status.stdout)
    assert status_payload["job"]["team_id"] == "team-test"

    replay = runner.invoke(app, ["team", "replay", "--job-id", payload["job"]["job_id"]])
    assert replay.exit_code == 0
    replay_payload = json.loads(replay.stdout)
    assert replay_payload["event_count"] >= 1


def test_team_init_produces_valid_yaml(tmp_path: Path) -> None:
    output = tmp_path / "team.yaml"
    init = runner.invoke(app, ["team", "init", "--output", str(output)])
    assert init.exit_code == 0
    validate = runner.invoke(app, ["team", "validate", "--spec", str(output), "--json"])
    assert validate.exit_code == 0


def test_team_init_regulated_template_produces_valid_yaml(tmp_path: Path) -> None:
    output = tmp_path / "team-regulated.yaml"
    init = runner.invoke(
        app,
        ["team", "init", "--output", str(output), "--template", "regulated"],
    )
    assert init.exit_code == 0
    validate = runner.invoke(app, ["team", "validate", "--spec", str(output), "--json"])
    assert validate.exit_code == 0


def test_team_resume_replays_approved_task_gate(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    spec_path = tmp_path / "team.json"
    policy_path = tmp_path / "policy.toml"
    _write_spec(spec_path)
    _write_task_approval_policy(policy_path)

    cfg = RuntimeConfig.from_profile("default").model_copy(
        update={
            "governance": RuntimeConfig.from_profile("default").governance.model_copy(
                update={
                    "policy_path": str(policy_path),
                    "approval_store_path": str(tmp_path / "approvals.sqlite3"),
                    "audit_dir": str(tmp_path / "audit"),
                }
            ),
            "team": RuntimeConfig.from_profile("default").team.model_copy(
                update={
                    "artifact_dir": str(tmp_path / "team_jobs"),
                    "checkpoint_db_path": str(tmp_path / "checkpoints.sqlite3"),
                }
            ),
        }
    )
    runtime = GovernanceRuntime(config=cfg)

    monkeypatch.setattr(
        "binliquid.cli.resolve_runtime_config",
        lambda *a, **k: (cfg, {}),
    )
    monkeypatch.setattr(
        "binliquid.cli._build_orchestrator",
        lambda *a, **k: ApprovalAwareFakeTeamOrchestrator(runtime),
    )

    first_run = runner.invoke(
        app,
        [
            "team",
            "run",
            "--spec",
            str(spec_path),
            "--once",
            "short request",
            "--json",
        ],
    )
    assert first_run.exit_code == 0
    first_payload = json.loads(first_run.stdout)
    assert first_payload["job"]["status"] == "blocked"

    approval_id = runtime.approval_store.list_pending()[0].approval_id
    approval = runtime.decide_approval(
        approval_id=approval_id,
        approve=True,
        actor="tester",
        reason="approved",
    )
    assert approval.error_code is None

    resume = runner.invoke(
        app,
        [
            "team",
            "resume",
            "--spec",
            str(spec_path),
            "--job-id",
            first_payload["job"]["job_id"],
            "--root-dir",
            str(tmp_path / "team_jobs"),
            "--json",
        ],
    )
    assert resume.exit_code == 0
    resume_payload = json.loads(resume.stdout)
    assert resume_payload["job"]["status"] == "completed"
    assert any(item["target"] == "task" for item in resume_payload["resolved_approvals"])
