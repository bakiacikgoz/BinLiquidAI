from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from binliquid.memory.authority import MemoryAuthority, build_memory_authority
from binliquid.memory.context_pack import (
    MemoryContextPack,
    context_pack_from_retrieval,
    empty_context_pack,
)
from binliquid.memory.models import (
    MemoryPolicyAction,
    MemoryPolicyDecision,
    MemoryRetrievalRequest,
    MemoryScope,
    MemoryScopeFilter,
    MemoryVisibility,
    MemoryWriteResult,
    hash_identity,
    stable_id,
)
from binliquid.memory.write_candidate import (
    MemoryWriteCandidateBuilder,
    MemoryWriteCandidateInput,
)
from binliquid.runtime.config import RuntimeConfig


@dataclass(frozen=True, slots=True)
class RuntimeMemoryRequest:
    run_id: str
    query: str
    actor_id: str
    requester_role: str
    agent_id: str | None = None
    team_id: str | None = None
    case_id: str | None = None
    project_id: str | None = None
    namespace: str = "default"


class MemoryRuntimeBridge:
    def __init__(
        self,
        *,
        config: RuntimeConfig,
        authority: MemoryAuthority,
        evidence_root: str | Path = "artifacts/memory-runtime",
    ) -> None:
        self.config = config
        self.authority = authority
        self.evidence_root = Path(evidence_root)

    @property
    def enabled(self) -> bool:
        return bool(self.config.memory.v3_enabled and self.config.memory.runtime.enabled)

    def retrieve_context(self, request: RuntimeMemoryRequest) -> MemoryContextPack:
        runtime_cfg = self.config.memory.runtime
        if not self.enabled:
            return empty_context_pack(
                run_id=request.run_id,
                query=request.query,
                status="disabled",
                degraded_reason="MEMORY_RUNTIME_DISABLED",
            )
        filters = _scope_filters(request)
        if not filters:
            status: Literal["degraded", "error"] = "degraded"
            reason = "MEMORY_RUNTIME_SCOPE_UNAVAILABLE"
            if self.config.profile_name in set(runtime_cfg.strict_fail_closed_profiles):
                status = "error"
                reason = "MEMORY_RUNTIME_FAIL_CLOSED_SCOPE_UNAVAILABLE"
            return empty_context_pack(
                run_id=request.run_id,
                query=request.query,
                status=status,
                degraded_reason=reason,
            )
        allowed_scopes = sorted({item.scope for item in filters}, key=str)
        result = self.authority.retrieve(
            MemoryRetrievalRequest(
                actorIdHash=hash_identity(request.actor_id),
                agentId=request.agent_id,
                requesterRole=request.requester_role,
                query=request.query,
                allowedScopes=allowed_scopes,
                scopeFilters=filters,
                visibilityFilters=_visibility_filters(filters),
                limit=max(1, runtime_cfg.context_top_k),
                includeContent=True,
                purpose="context_injection",
            )
        )
        return context_pack_from_retrieval(
            run_id=request.run_id,
            result=result,
            max_context_chars=runtime_cfg.max_context_chars,
        )

    def propose_post_run_write(
        self,
        *,
        run_id: str,
        actor_id: str,
        role: str,
        user_input: str,
        assistant_output: str,
        scope: str | None = None,
        owner_type: str | None = None,
        owner: str | None = None,
        visibility: str | None = None,
        memory_target: str | None = None,
        expected_state_version: int | None = None,
        agent_id: str | None = None,
    ) -> MemoryWriteResult:
        if not self.enabled or not self.config.memory.runtime.post_run_write_enabled:
            return _disabled_write_result(run_id=run_id, reason="MEMORY_RUNTIME_WRITE_DISABLED")
        resolved_scope = scope or self.config.memory.runtime.post_run_default_scope
        resolved_owner_type = owner_type or _owner_type_for_scope(resolved_scope)
        resolved_visibility = visibility or _visibility_for_scope(resolved_scope)
        proposal = MemoryWriteCandidateBuilder.build(
            MemoryWriteCandidateInput(
                actor=actor_id,
                role=role,
                run_id=run_id,
                user_input=user_input,
                assistant_output=assistant_output,
                scope=resolved_scope,
                owner_type=resolved_owner_type,
                owner=owner or actor_id,
                visibility=resolved_visibility,
                memory_target=memory_target,
                expected_state_version=expected_state_version,
                agent_id=agent_id,
            )
        )
        if proposal is None:
            return _disabled_write_result(run_id=run_id, reason="MEMORY_RUNTIME_WRITE_EMPTY")
        return self.authority.propose_write(proposal)


def build_memory_runtime_bridge(
    config: RuntimeConfig,
    *,
    evidence_root: str | Path = "artifacts/memory-runtime",
) -> MemoryRuntimeBridge:
    return MemoryRuntimeBridge(
        config=config,
        authority=build_memory_authority(config, evidence_root=evidence_root),
        evidence_root=evidence_root,
    )


def _scope_filters(request: RuntimeMemoryRequest) -> list[MemoryScopeFilter]:
    filters = [
        MemoryScopeFilter(
            scope=MemoryScope.PERSONAL,
            ownerType="user",
            ownerIdHash=hash_identity(request.actor_id),
            namespace=request.namespace,
        )
    ]
    if request.agent_id:
        filters.append(
            MemoryScopeFilter(
                scope=MemoryScope.AGENT,
                ownerType="agent",
                ownerIdHash=hash_identity(request.agent_id),
                namespace=request.namespace,
            )
        )
    if request.team_id:
        filters.append(
            MemoryScopeFilter(
                scope=MemoryScope.TEAM,
                ownerType="team",
                ownerIdHash=hash_identity(request.team_id),
                namespace=request.namespace,
            )
        )
    if request.case_id:
        filters.append(
            MemoryScopeFilter(
                scope=MemoryScope.CASE,
                ownerType="case",
                ownerIdHash=hash_identity(request.case_id),
                namespace=request.namespace,
            )
        )
    if request.project_id:
        filters.append(
            MemoryScopeFilter(
                scope=MemoryScope.PROJECT,
                ownerType="project",
                ownerIdHash=hash_identity(request.project_id),
                namespace=request.namespace,
            )
        )
    return filters


def _visibility_filters(filters: list[MemoryScopeFilter]) -> list[MemoryVisibility]:
    values: set[MemoryVisibility] = {MemoryVisibility.PRIVATE}
    for item in filters:
        if item.scope == MemoryScope.AGENT:
            values.add(MemoryVisibility.AGENT)
        elif item.scope == MemoryScope.TEAM:
            values.add(MemoryVisibility.TEAM)
        elif item.scope == MemoryScope.PROJECT:
            values.add(MemoryVisibility.PROJECT)
    return sorted(values, key=str)


def _owner_type_for_scope(scope: str) -> str:
    return {
        "agent": "agent",
        "team": "team",
        "case": "case",
        "project": "project",
        "organization": "org",
    }.get(scope, "user")


def _visibility_for_scope(scope: str) -> str:
    return {
        "agent": "agent",
        "team": "team",
        "case": "team",
        "project": "project",
        "organization": "organization",
    }.get(scope, "private")


def _disabled_write_result(*, run_id: str, reason: str) -> MemoryWriteResult:
    return MemoryWriteResult(
        status="error",
        proposalId=stable_id("mem_prop", run_id, reason),
        policyDecision=MemoryPolicyDecision(
            decision=MemoryPolicyAction.DENY,
            reasonCode=reason,
            blockingReasons=[reason],
        ),
        blockingReasons=[reason],
        rawContentIncluded=False,
    )
