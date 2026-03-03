from __future__ import annotations

from dataclasses import dataclass

from binliquid.governance.models import GovernanceAction
from binliquid.governance.runtime import GovernanceRuntime
from binliquid.memory.manager import MemoryManager


@dataclass(slots=True)
class MemoryScopeDecision:
    allowed: bool
    requires_approval: bool
    reason_code: str
    approval_id: str | None


def evaluate_memory_scope_write(
    *,
    governance_runtime: GovernanceRuntime | None,
    run_id: str,
    scope: str,
    producer_role: str,
    visibility: str,
    override_approval_id: str | None = None,
) -> MemoryScopeDecision:
    if governance_runtime is None:
        return MemoryScopeDecision(
            allowed=True,
            requires_approval=False,
            reason_code="RULE_ROUTE",
            approval_id=None,
        )

    decision, ticket = governance_runtime.evaluate_memory_write(
        run_id=run_id,
        scope=scope,
        producer_role=producer_role,
        visibility=visibility,
        override_approval_id=override_approval_id,
    )

    if decision.action == GovernanceAction.DENY:
        return MemoryScopeDecision(
            allowed=False,
            requires_approval=False,
            reason_code=decision.reason_code,
            approval_id=None,
        )
    if decision.action == GovernanceAction.REQUIRE_APPROVAL:
        return MemoryScopeDecision(
            allowed=False,
            requires_approval=True,
            reason_code=decision.reason_code,
            approval_id=ticket.approval_id if ticket else None,
        )

    return MemoryScopeDecision(
        allowed=True,
        requires_approval=False,
        reason_code=decision.reason_code,
        approval_id=None,
    )


def write_scoped_memory(
    *,
    memory_manager: MemoryManager | None,
    session_id: str,
    task_type: str,
    user_input: str,
    assistant_output: str,
    scope: str,
    team_id: str,
    case_id: str,
    job_id: str,
    producer_agent_id: str,
    producer_role: str,
    visibility: str,
) -> dict[str, object]:
    if memory_manager is None:
        return {
            "written": False,
            "reason": "memory_manager_missing",
            "record_id": None,
            "salience_score": 0.0,
        }

    writer = getattr(memory_manager, "maybe_write_scoped", None)
    if callable(writer):
        result = writer(
            session_id=session_id,
            task_type=task_type,
            user_input=user_input,
            assistant_output=assistant_output,
            scope=scope,
            team_id=team_id,
            case_id=case_id,
            job_id=job_id,
            producer_agent_id=producer_agent_id,
            producer_role=producer_role,
            visibility=visibility,
            expert_payload=None,
        )
        return {
            "written": result.written,
            "reason": result.reason,
            "record_id": result.record_id,
            "salience_score": result.salience_score,
        }

    # Backward-compatible fallback for older MemoryManager API.
    result = memory_manager.maybe_write(
        session_id=session_id,
        task_type=task_type,
        user_input=user_input,
        assistant_output=assistant_output,
        expert_payload=None,
    )
    return {
        "written": result.written,
        "reason": result.reason,
        "record_id": result.record_id,
        "salience_score": result.salience_score,
    }
