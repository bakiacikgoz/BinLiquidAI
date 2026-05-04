from __future__ import annotations

import json
from pathlib import Path

import jsonschema
from typer.testing import CliRunner

from binliquid.cli import app
from binliquid.contracts import (
    ApprovalDetailPayloadContract,
    ApprovalPendingPayloadContract,
    OperatorCapabilitiesPayload,
    PreviewFixtureBundleContract,
    RunReplayPayloadContract,
    RunSummaryPayloadContract,
    TeamStatusArtifactContract,
)
from binliquid.governance.runtime import GovernanceRuntime
from binliquid.runtime.config import RuntimeConfig
from binliquid.runtime.platform import current_platform
from binliquid.schemas.models import OrchestratorResult

runner = CliRunner()


class _FakeTeamOrchestrator:
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


class _ApprovalAwareFakeTeamOrchestrator:
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
        run_id = str(
            session_context.get("governance_run_id")
            or session_context.get("job_id")
            or "job-test"
        )
        override_id = session_context.get("governance_approval_id")
        decision, ticket = self.governance_runtime.evaluate_task(
            run_id=run_id,
            task_type="chat",
            user_input=user_input,
            override_approval_id=override_id,
            execution_contract_hash=session_context.get("governance_execution_contract_hash"),
            resume_token_ref=session_context.get("governance_resume_token_ref"),
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
            "termination_rules": {"max_tasks": 8, "max_retries": 1, "max_handoff_depth": 8},
        },
        "tasks": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_task_approval_policy(path: Path) -> None:
    path.write_text(
        """
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
""".strip(),
        encoding="utf-8",
    )


def test_preview_fixture_bundle_validates_against_contracts() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "contracts"
        / "operator_panel"
        / "fixtures"
        / "operator_panel_preview.json"
    )
    fixture = PreviewFixtureBundleContract.model_validate_json(
        fixture_path.read_text(encoding="utf-8")
    )
    assert fixture.contract_version == "2.0"
    assert (
        fixture.handshake.capabilities.features.computer_use_pilot.adapter_status
        == "safari_applescript"
    )


def test_operator_capabilities_payload_matches_contract() -> None:
    result = runner.invoke(app, ["operator", "capabilities", "--json"])
    assert result.exit_code == 0
    payload = OperatorCapabilitiesPayload.model_validate_json(result.stdout)
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "contracts"
        / "operator_panel"
        / "schemas"
        / "operator_capabilities.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(json.loads(result.stdout))

    assert payload.contract_version == "2.0"
    if current_platform().label == "windows":
        assert payload.features.computer_use_pilot.enabled is False
        assert (
            payload.features.computer_use_pilot.reason_code
            == "WINDOWS_COMPUTER_USE_NOT_QUALIFIED"
        )
        assert payload.features.computer_use_pilot.adapter_status == "windows_scaffold"
    else:
        assert payload.features.computer_use_pilot.adapter_status == "safari_applescript"


def test_team_runtime_payloads_match_frozen_contracts(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    spec_path = tmp_path / "team.json"
    _write_spec(spec_path)

    monkeypatch.setattr(
        "binliquid.cli._build_orchestrator",
        lambda *a, **k: _FakeTeamOrchestrator(),
    )

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
    run_payload = json.loads(run.stdout)
    job_id = run_payload["job"]["job_id"]

    listed = runner.invoke(app, ["team", "list", "--json"])
    assert listed.exit_code == 0
    listed_payload = RunSummaryPayloadContract.model_validate_json(listed.stdout)
    assert listed_payload.contract_version == "2.0"
    assert listed_payload.count == 1

    status = runner.invoke(app, ["team", "status", "--job-id", job_id, "--json"])
    assert status.exit_code == 0
    status_payload = TeamStatusArtifactContract.model_validate_json(status.stdout)
    assert status_payload.contract_version == "2.0"
    assert status_payload.job.job_id == job_id

    replay = runner.invoke(app, ["team", "replay", "--job-id", job_id, "--json"])
    assert replay.exit_code == 0
    replay_payload = RunReplayPayloadContract.model_validate_json(replay.stdout)
    assert replay_payload.contract_version == "2.0"
    assert replay_payload.job_id == job_id

    status_artifact = TeamStatusArtifactContract.model_validate_json(
        (tmp_path / ".binliquid" / "team" / "jobs" / job_id / "status.json").read_text(
            encoding="utf-8"
        )
    )
    assert status_artifact.contract_version == "2.0"


def test_approval_payloads_match_frozen_contracts(monkeypatch, tmp_path: Path) -> None:
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

    monkeypatch.setattr("binliquid.cli.resolve_runtime_config", lambda *a, **k: (cfg, {}))
    monkeypatch.setattr("binliquid.cli.RuntimeConfig.from_profile", lambda *_: cfg)
    monkeypatch.setattr(
        "binliquid.cli._build_orchestrator",
        lambda *a, **k: _ApprovalAwareFakeTeamOrchestrator(runtime),
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

    pending = runner.invoke(app, ["approval", "pending", "--json"])
    assert pending.exit_code == 0
    pending_payload = ApprovalPendingPayloadContract.model_validate_json(pending.stdout)
    assert pending_payload.contract_version == "2.0"
    assert len(pending_payload.pending) == 1

    approval_id = pending_payload.pending[0].approval_id
    detail = runner.invoke(app, ["approval", "show", "--id", approval_id, "--json"])
    assert detail.exit_code == 0
    detail_payload = ApprovalDetailPayloadContract.model_validate_json(detail.stdout)
    assert detail_payload.contract_version == "2.0"
    assert detail_payload.ticket.approval_id == approval_id
