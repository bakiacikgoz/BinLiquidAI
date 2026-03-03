from __future__ import annotations

import json
from pathlib import Path

from binliquid.governance.runtime import GovernanceRuntime
from binliquid.runtime.config import RuntimeConfig
from binliquid.schemas.models import OrchestratorResult
from binliquid.team.models import TeamSpec
from binliquid.team.supervisor import TeamSupervisor


class _EnvelopeOrchestrator:
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
            trace_id="trace-envelope",
            metrics={"router_reason_code": "RULE_ROUTE"},
        )


def test_team_audit_envelope_contains_policy_and_runtime_hashes(tmp_path: Path) -> None:
    cfg = RuntimeConfig.from_profile("default")
    cfg = cfg.model_copy(
        update={
            "governance": cfg.governance.model_copy(
                update={
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
    supervisor = TeamSupervisor(orchestrator=_EnvelopeOrchestrator(runtime), config=cfg)

    spec = TeamSpec.model_validate(
        {
            "version": "1",
            "team": {
                "team_id": "team-envelope",
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
                "supervisor_policy": "sequential_then_parallel",
                "handoff_rules": [],
                "termination_rules": {
                    "max_tasks": 8,
                    "max_retries": 1,
                    "max_handoff_depth": 8,
                },
            },
            "tasks": [],
        }
    )

    result = supervisor.run(spec=spec, request="hello", case_id="case-1", job_id="job-1")
    assert result.audit_envelope_path is not None
    envelope_path = Path(result.audit_envelope_path)
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))

    assert envelope["policy_bundle_id"]
    assert len(envelope["policy_bundle_hash"]) == 64
    assert len(envelope["runtime_config_hash"]) == 64
    assert len(envelope["integrity"]["hash"]) == 64
