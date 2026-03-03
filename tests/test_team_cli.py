from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from binliquid.cli import app
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
