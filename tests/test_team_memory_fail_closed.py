from __future__ import annotations

from pathlib import Path

from binliquid.governance.runtime import GovernanceRuntime
from binliquid.runtime.config import RuntimeConfig
from binliquid.schemas.models import OrchestratorResult
from binliquid.team.models import TeamSpec
from binliquid.team.supervisor import TeamSupervisor

DENY_MEMORY_POLICY = """
policy_schema_version = "1.0"
policy_version = "team-deny-memory"
web_egress = "deny"

[[task_rules]]
id = "task-chat-allow"
task_types = ["chat", "plan", "research", "code", "mixed"]
action = "allow"

[[tool_rules]]
id = "tool-python"
command_roots = ["python", "uv", "pytest", "ruff", "rg"]
action = "allow"
arg_deny_regex = []

[[memory_scope_rules]]
id = "deny-case"
scopes = ["case"]
producer_roles = []
visibilities = ["team"]
action = "deny"

[[handoff_rules]]
id = "allow-all"
from_roles = []
to_roles = []
action = "allow"

[pii_rules]
patterns = []
"""


class FakeTeamOrchestrator:
    def __init__(self, runtime: GovernanceRuntime):
        self.governance_runtime = runtime
        self._memory_manager = None

    def process(
        self,
        user_input: str,
        session_context: dict[str, str] | None = None,
        use_router: bool = True,
    ) -> OrchestratorResult:
        del user_input, session_context, use_router
        return OrchestratorResult(
            final_text="ok",
            used_path="llm_only",
            fallback_events=[],
            trace_id="trace-1",
            metrics={"router_reason_code": "RULE_ROUTE"},
        )


def test_team_runtime_blocks_on_memory_scope_deny(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.toml"
    policy_path.write_text(DENY_MEMORY_POLICY, encoding="utf-8")

    cfg = RuntimeConfig.from_profile("default")
    cfg = cfg.model_copy(
        update={
            "governance": cfg.governance.model_copy(
                update={
                    "policy_path": str(policy_path),
                    "approval_store_path": str(tmp_path / "approvals.sqlite3"),
                    "audit_dir": str(tmp_path / "audit"),
                }
            ),
            "team": cfg.team.model_copy(
                update={
                    "artifact_dir": str(tmp_path / "team_jobs"),
                    "checkpoint_db_path": str(tmp_path / "checkpoints.sqlite3"),
                }
            ),
        }
    )
    runtime = GovernanceRuntime(config=cfg)
    orchestrator = FakeTeamOrchestrator(runtime)
    supervisor = TeamSupervisor(orchestrator=orchestrator, config=cfg)

    spec = TeamSpec.model_validate(
        {
            "version": "1",
            "team": {
                "team_id": "team-deny",
                "agents": [
                    {
                        "agent_id": "agent-intake",
                        "role": "Intake Agent",
                        "allowed_task_types": ["chat", "plan"],
                        "profile_name": "balanced",
                        "model_overrides": {},
                        "memory_scope_access": ["case"],
                        "tool_policy_profile": "default",
                        "approval_mode": "auto",
                    }
                ],
                "supervisor_policy": "sequential_then_parallel",
                "handoff_rules": [],
                "termination_rules": {
                    "max_tasks": 8,
                    "max_retries": 1,
                    "max_handoff_depth": 8,
                },
            },
            "tasks": [
                {
                    "task_id": "task-1",
                    "title": "only",
                    "task_type": "chat",
                    "role": "Intake Agent",
                    "depends_on": [],
                    "input_template": "{{request}}",
                }
            ],
        }
    )

    result = supervisor.run(spec=spec, request="hello", case_id="case-1", job_id="job-1")

    assert result.job.status.value == "blocked"
    assert any(task.reason_code == "MEMORY_SCOPE_DENY" for task in result.tasks)
