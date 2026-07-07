from __future__ import annotations

from pathlib import Path
from typing import Any

from binliquid.assistant_tasking.models import AgentTaskCandidate
from binliquid.control_plane.agent_enrollment import (
    EnterpriseEnrollmentError,
    require_active_enrollment,
)
from binliquid.control_plane.registry import AgentRegistry


def resolve_agent_candidates(
    *,
    root_dir: str | Path,
    workspace_id: str,
    agent_hint: str | None = None,
) -> tuple[AgentTaskCandidate, ...]:
    registry = AgentRegistry(root_dir=root_dir)
    records = registry.list_agents()
    if agent_hint:
        records = [record for record in records if record.agent_id == agent_hint]
        if not records:
            return (
                AgentTaskCandidate(
                    agentId=agent_hint,
                    label=agent_hint,
                    enrolled=False,
                    workspaceId=workspace_id,
                    allowedSurfaces=(),
                    blockedSurfaces=("external_gateway", "team_runtime"),
                    declaredActions=(),
                    qualificationStatus="unknown",
                    blockingReasons=("ASSISTANT_TASK_UNKNOWN_AGENT_DENIED",),
                ),
            )
    candidates: list[AgentTaskCandidate] = []
    for record in records:
        metadata = record.spec.metadata
        candidate_workspace = _metadata_string(metadata, "workspace_id") or workspace_id
        enrolled, enrollment_reason = _enrollment_status(
            root_dir=root_dir,
            agent_id=record.agent_id,
            workspace_id=candidate_workspace,
        )
        blocking: list[str] = []
        if candidate_workspace != workspace_id:
            blocking.append("ASSISTANT_TASK_CROSS_WORKSPACE_DENIED")
        if not enrolled:
            blocking.append(enrollment_reason or "ASSISTANT_TASK_UNENROLLED_AGENT_DENIED")
        runtime_kind = str(record.spec.runtime_kind)
        allowed = (
            ("external_gateway",)
            if runtime_kind in {"external_stdio", "external_http"}
            else ()
        )
        blocked = () if allowed else ("external_gateway",)
        candidates.append(
            AgentTaskCandidate(
                agentId=record.agent_id,
                label=record.spec.display_name,
                enrolled=enrolled,
                workspaceId=candidate_workspace,
                principalId=_metadata_string(metadata, "principal_id"),
                allowedSurfaces=allowed,
                blockedSurfaces=blocked,
                declaredActions=("read", "external_write"),
                qualificationStatus="ready" if enrolled and allowed else "blocked",
                blockingReasons=tuple(blocking),
            )
        )
    return tuple(candidates)


def select_candidate(candidates: tuple[AgentTaskCandidate, ...]) -> AgentTaskCandidate | None:
    for candidate in candidates:
        if candidate.enrolled and not candidate.blocking_reasons:
            return candidate
    return candidates[0] if candidates else None


def _enrollment_status(
    *,
    root_dir: str | Path,
    agent_id: str,
    workspace_id: str | None,
) -> tuple[bool, str | None]:
    try:
        require_active_enrollment(agent_id=agent_id, workspace_id=workspace_id, root_dir=root_dir)
    except EnterpriseEnrollmentError as exc:
        if exc.error_code == "AGENT_NOT_ENROLLED":
            return False, "ASSISTANT_TASK_UNENROLLED_AGENT_DENIED"
        return False, exc.error_code
    return True, None


def _metadata_string(metadata: dict[str, Any], key: str) -> str | None:
    value = metadata.get(key)
    return value if isinstance(value, str) and value.strip() else None
