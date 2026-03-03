from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from binliquid import __version__
from binliquid.governance.approval_store import ApprovalDecisionResult, ApprovalStore
from binliquid.governance.models import (
    ApprovalTicket,
    AuditRecord,
    GovernanceAction,
    GovernanceDecision,
    GovernancePhase,
    HandoffCallRecord,
    MemoryWriteRecord,
    ToolCallRecord,
)
from binliquid.governance.policy import (
    PolicyBundle,
    evaluate_handoff,
    evaluate_memory_scope_write,
    evaluate_task,
    evaluate_tool,
    load_policy,
    normalize_command,
)
from binliquid.governance.redaction import (
    fingerprint_args,
    redact_audit_payload,
    redact_trace_payload,
)
from binliquid.runtime.config import GovernanceConfig, RuntimeConfig


@dataclass(slots=True)
class GovernanceRunState:
    decisions: list[GovernanceDecision] = field(default_factory=list)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    handoffs: list[HandoffCallRecord] = field(default_factory=list)
    memory_writes: list[MemoryWriteRecord] = field(default_factory=list)
    approval_status: str = "none"


class GovernanceRuntime:
    def __init__(self, *, config: RuntimeConfig):
        self._config = config
        self._gov = config.governance
        self._policy_bundle: PolicyBundle | None = None
        self._policy_error: str | None = None
        self._runs: dict[str, GovernanceRunState] = {}
        self._approval_store = ApprovalStore(self._gov.approval_store_path)
        self._audit_dir = Path(self._gov.audit_dir)
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        self._load_policy()

    @property
    def enabled(self) -> bool:
        return self._gov.enabled

    @property
    def policy_available(self) -> bool:
        return self._policy_bundle is not None

    @property
    def policy_error(self) -> str | None:
        return self._policy_error

    @property
    def approval_store(self) -> ApprovalStore:
        return self._approval_store

    def _load_policy(self) -> None:
        if not self._gov.enabled:
            return
        try:
            self._policy_bundle = load_policy(self._gov.policy_path)
            self._policy_error = None
        except Exception as exc:  # noqa: BLE001
            self._policy_bundle = None
            self._policy_error = str(exc)

    def execution_startup_error(self) -> str | None:
        if not self._gov.enabled:
            return None
        if self._policy_bundle is not None:
            return None
        if self._gov.policy_fail_mode == "fail_closed":
            return self._policy_error or "POLICY_UNAVAILABLE"
        return None

    def evaluate_task(
        self,
        *,
        run_id: str,
        task_type: str,
        user_input: str,
        override_approval_id: str | None = None,
    ) -> tuple[GovernanceDecision, ApprovalTicket | None]:
        if not self._gov.enabled:
            decision = self._default_allow_decision(phase=GovernancePhase.TASK, target=task_type)
            return decision, None
        if self._policy_bundle is None:
            decision = GovernanceDecision(
                phase=GovernancePhase.TASK,
                target=task_type,
                action=GovernanceAction.DENY,
                reason_code="POLICY_UNAVAILABLE",
                matched_rule_path=None,
                policy_schema_version="unavailable",
                policy_version="unavailable",
                policy_hash="unavailable",
                decision_engine_version=self._gov.decision_engine_version,
                explain=self._policy_error,
            )
            self._record_decision(run_id, decision)
            return decision, None

        if override_approval_id:
            ticket = self._approval_store.get(override_approval_id)
            if ticket and ticket.status.value in {"approved", "executed"}:
                decision = GovernanceDecision(
                    phase=GovernancePhase.TASK,
                    target=task_type,
                    action=GovernanceAction.ALLOW,
                    reason_code="APPROVAL_PENDING",
                    matched_rule_path="approval_override",
                    policy_schema_version=self._policy_bundle.policy.policy_schema_version,
                    policy_version=self._policy_bundle.policy.policy_version,
                    policy_hash=self._policy_bundle.policy_hash,
                    decision_engine_version=self._gov.decision_engine_version,
                    approval_required=False,
                    approval_id=ticket.approval_id,
                    explain="approved override",
                )
                self._record_decision(run_id, decision)
                return decision, None

        match = evaluate_task(self._policy_bundle.policy, task_type=task_type)
        decision = GovernanceDecision(
            phase=GovernancePhase.TASK,
            target=task_type,
            action=match.action,
            reason_code=match.reason_code,
            matched_rule_path=match.matched_rule_path,
            policy_schema_version=self._policy_bundle.policy.policy_schema_version,
            policy_version=self._policy_bundle.policy.policy_version,
            policy_hash=self._policy_bundle.policy_hash,
            decision_engine_version=self._gov.decision_engine_version,
            approval_required=match.action == GovernanceAction.REQUIRE_APPROVAL,
            explain=match.explain,
        )

        ticket: ApprovalTicket | None = None
        if decision.action == GovernanceAction.REQUIRE_APPROVAL:
            request_hash = self._hash_payload({"task_type": task_type, "user_input": user_input})
            snapshot = {
                "kind": "task",
                "task_type": task_type,
                "user_input": user_input,
                "run_id": run_id,
                "policy_hash": self._policy_bundle.policy_hash,
            }
            snapshot_hash = self._hash_payload(snapshot)
            ticket = self._approval_store.create_ticket(
                run_id=run_id,
                request_hash=request_hash,
                snapshot_hash=snapshot_hash,
                snapshot=snapshot,
                ttl_seconds=self._gov.approval_ttl_seconds,
                idempotency_key=f"task:{run_id}:{snapshot_hash}",
            )
            decision = decision.model_copy(update={"approval_id": ticket.approval_id})
            self._set_approval_status(run_id, "pending")

        self._record_decision(run_id, decision)
        return decision, ticket

    def evaluate_tool_command(
        self,
        *,
        run_id: str,
        command: list[str],
        workdir: str | Path,
    ) -> tuple[GovernanceDecision, ApprovalTicket | None, list[str]]:
        if not self._gov.enabled:
            decision = self._default_allow_decision(phase=GovernancePhase.TOOL, target="")
            return decision, None, command[1:]
        if self._policy_bundle is None:
            decision = GovernanceDecision(
                phase=GovernancePhase.TOOL,
                target=command[0] if command else "",
                action=GovernanceAction.DENY,
                reason_code="POLICY_UNAVAILABLE",
                matched_rule_path=None,
                policy_schema_version="unavailable",
                policy_version="unavailable",
                policy_hash="unavailable",
                decision_engine_version=self._gov.decision_engine_version,
                explain=self._policy_error,
            )
            self._record_decision(run_id, decision)
            return decision, None, command[1:]

        command_root, normalized_args = normalize_command(command, workdir=workdir)
        match = evaluate_tool(
            self._policy_bundle.policy,
            command_root=command_root,
            args=normalized_args,
        )
        decision = GovernanceDecision(
            phase=GovernancePhase.TOOL,
            target=command_root,
            action=match.action,
            reason_code=match.reason_code,
            matched_rule_path=match.matched_rule_path,
            policy_schema_version=self._policy_bundle.policy.policy_schema_version,
            policy_version=self._policy_bundle.policy.policy_version,
            policy_hash=self._policy_bundle.policy_hash,
            decision_engine_version=self._gov.decision_engine_version,
            approval_required=match.action == GovernanceAction.REQUIRE_APPROVAL,
            explain=match.explain,
        )
        ticket: ApprovalTicket | None = None
        if match.action == GovernanceAction.REQUIRE_APPROVAL:
            snapshot = {
                "kind": "tool",
                "command": command,
                "normalized": [command_root, *normalized_args],
                "run_id": run_id,
                "policy_hash": self._policy_bundle.policy_hash,
            }
            request_hash = self._hash_payload(snapshot["normalized"])
            snapshot_hash = self._hash_payload(snapshot)
            ticket = self._approval_store.create_ticket(
                run_id=run_id,
                request_hash=request_hash,
                snapshot_hash=snapshot_hash,
                snapshot=snapshot,
                ttl_seconds=self._gov.approval_ttl_seconds,
                idempotency_key=f"tool:{run_id}:{snapshot_hash}",
            )
            decision = decision.model_copy(update={"approval_id": ticket.approval_id})
            self._set_approval_status(run_id, "pending")

        tool_record = ToolCallRecord(
            command_root=command_root,
            args_fingerprint=fingerprint_args(
                normalized_args,
                pii_patterns=self._policy_bundle.policy.pii_rules.patterns,
            ),
            decision_action=decision.action,
            reason_code=decision.reason_code,
        )
        self._record_tool_call(run_id, tool_record)
        self._record_decision(run_id, decision)
        return decision, ticket, normalized_args

    def evaluate_handoff(
        self,
        *,
        run_id: str,
        from_role: str,
        to_role: str,
        payload: dict[str, Any],
    ) -> tuple[GovernanceDecision, ApprovalTicket | None]:
        if not self._gov.enabled:
            decision = self._default_allow_decision(
                phase=GovernancePhase.HANDOFF,
                target=f"{from_role}->{to_role}",
            )
            return decision, None
        if self._policy_bundle is None:
            decision = GovernanceDecision(
                phase=GovernancePhase.HANDOFF,
                target=f"{from_role}->{to_role}",
                action=GovernanceAction.DENY,
                reason_code="POLICY_UNAVAILABLE",
                matched_rule_path=None,
                policy_schema_version="unavailable",
                policy_version="unavailable",
                policy_hash="unavailable",
                decision_engine_version=self._gov.decision_engine_version,
                explain=self._policy_error,
            )
            self._record_decision(run_id, decision)
            return decision, None

        match = evaluate_handoff(
            self._policy_bundle.policy,
            from_role=from_role,
            to_role=to_role,
        )
        decision = GovernanceDecision(
            phase=GovernancePhase.HANDOFF,
            target=f"{from_role}->{to_role}",
            action=match.action,
            reason_code=match.reason_code,
            matched_rule_path=match.matched_rule_path,
            policy_schema_version=self._policy_bundle.policy.policy_schema_version,
            policy_version=self._policy_bundle.policy.policy_version,
            policy_hash=self._policy_bundle.policy_hash,
            decision_engine_version=self._gov.decision_engine_version,
            approval_required=match.action == GovernanceAction.REQUIRE_APPROVAL,
            explain=match.explain,
        )

        ticket: ApprovalTicket | None = None
        payload_hash = self._hash_payload(payload)
        if match.action == GovernanceAction.REQUIRE_APPROVAL:
            snapshot = {
                "kind": "handoff",
                "from_role": from_role,
                "to_role": to_role,
                "payload_hash": payload_hash,
                "run_id": run_id,
                "policy_hash": self._policy_bundle.policy_hash,
            }
            request_hash = self._hash_payload([from_role, to_role, payload_hash])
            snapshot_hash = self._hash_payload(snapshot)
            ticket = self._approval_store.create_ticket(
                run_id=run_id,
                request_hash=request_hash,
                snapshot_hash=snapshot_hash,
                snapshot=snapshot,
                ttl_seconds=self._gov.approval_ttl_seconds,
                idempotency_key=f"handoff:{run_id}:{snapshot_hash}",
            )
            decision = decision.model_copy(update={"approval_id": ticket.approval_id})
            self._set_approval_status(run_id, "pending")

        self._record_handoff(
            run_id,
            HandoffCallRecord(
                from_role=from_role,
                to_role=to_role,
                payload_hash=payload_hash,
                decision_action=decision.action,
                reason_code=decision.reason_code,
            ),
        )
        self._record_decision(run_id, decision)
        return decision, ticket

    def evaluate_memory_write(
        self,
        *,
        run_id: str,
        scope: str,
        producer_role: str,
        visibility: str,
    ) -> tuple[GovernanceDecision, ApprovalTicket | None]:
        if not self._gov.enabled:
            decision = self._default_allow_decision(
                phase=GovernancePhase.MEMORY_WRITE,
                target=f"{scope}:{producer_role}:{visibility}",
            )
            return decision, None
        if self._policy_bundle is None:
            decision = GovernanceDecision(
                phase=GovernancePhase.MEMORY_WRITE,
                target=f"{scope}:{producer_role}:{visibility}",
                action=GovernanceAction.DENY,
                reason_code="POLICY_UNAVAILABLE",
                matched_rule_path=None,
                policy_schema_version="unavailable",
                policy_version="unavailable",
                policy_hash="unavailable",
                decision_engine_version=self._gov.decision_engine_version,
                explain=self._policy_error,
            )
            self._record_decision(run_id, decision)
            return decision, None

        match = evaluate_memory_scope_write(
            self._policy_bundle.policy,
            scope=scope,
            producer_role=producer_role,
            visibility=visibility,
        )
        decision = GovernanceDecision(
            phase=GovernancePhase.MEMORY_WRITE,
            target=f"{scope}:{producer_role}:{visibility}",
            action=match.action,
            reason_code=match.reason_code,
            matched_rule_path=match.matched_rule_path,
            policy_schema_version=self._policy_bundle.policy.policy_schema_version,
            policy_version=self._policy_bundle.policy.policy_version,
            policy_hash=self._policy_bundle.policy_hash,
            decision_engine_version=self._gov.decision_engine_version,
            approval_required=match.action == GovernanceAction.REQUIRE_APPROVAL,
            explain=match.explain,
        )

        ticket: ApprovalTicket | None = None
        if match.action == GovernanceAction.REQUIRE_APPROVAL:
            snapshot = {
                "kind": "memory_write",
                "scope": scope,
                "producer_role": producer_role,
                "visibility": visibility,
                "run_id": run_id,
                "policy_hash": self._policy_bundle.policy_hash,
            }
            request_hash = self._hash_payload([scope, producer_role, visibility])
            snapshot_hash = self._hash_payload(snapshot)
            ticket = self._approval_store.create_ticket(
                run_id=run_id,
                request_hash=request_hash,
                snapshot_hash=snapshot_hash,
                snapshot=snapshot,
                ttl_seconds=self._gov.approval_ttl_seconds,
                idempotency_key=f"memory:{run_id}:{snapshot_hash}",
            )
            decision = decision.model_copy(update={"approval_id": ticket.approval_id})
            self._set_approval_status(run_id, "pending")

        self._record_memory_write(
            run_id,
            MemoryWriteRecord(
                scope=scope,
                producer_role=producer_role,
                visibility=visibility,
                decision_action=decision.action,
                reason_code=decision.reason_code,
            ),
        )
        self._record_decision(run_id, decision)
        return decision, ticket

    def trace_redact(self, data: dict[str, Any]) -> dict[str, Any]:
        patterns = []
        if self._policy_bundle is not None:
            patterns = self._policy_bundle.policy.pii_rules.patterns
        return redact_trace_payload(data, pii_patterns=patterns)

    def audit_redact(self, data: dict[str, Any]) -> dict[str, Any]:
        patterns = []
        if self._policy_bundle is not None:
            patterns = self._policy_bundle.policy.pii_rules.patterns
        return redact_audit_payload(data, pii_patterns=patterns)

    def finalize_run(
        self,
        *,
        run_id: str,
        router_reason_code: str | None,
        model_metadata: dict[str, Any] | None = None,
    ) -> str | None:
        if not self._gov.enabled:
            return None
        if self._policy_bundle is None:
            return None
        state = self._runs.get(run_id, GovernanceRunState())
        model_metadata = model_metadata or {}

        requested_provider = str(
            model_metadata.get("requested_provider")
            or self._config.llm_provider
        )
        requested_model_name = str(
            model_metadata.get("requested_model_name")
            or self._config.model_name
        )

        record = AuditRecord(
            run_id=run_id,
            runtime_version=__version__,
            profile=self._config.profile_name,
            model_provider=requested_provider,
            model_name=requested_model_name,
            requested_provider=requested_provider,
            requested_fallback_provider=str(
                model_metadata.get("requested_fallback_provider")
                or self._config.fallback_provider
            ),
            requested_model_name=requested_model_name,
            requested_hf_model_id=str(
                model_metadata.get("requested_hf_model_id")
                or self._config.hf_model_id
            ),
            selected_provider=(
                str(model_metadata["selected_provider"])
                if model_metadata.get("selected_provider") is not None
                else None
            ),
            selected_model_name=(
                str(model_metadata["selected_model_name"])
                if model_metadata.get("selected_model_name") is not None
                else None
            ),
            selected_hf_model_id=(
                str(model_metadata["selected_hf_model_id"])
                if model_metadata.get("selected_hf_model_id") is not None
                else None
            ),
            fallback_used=bool(model_metadata.get("fallback_used", False)),
            config_source_model_name=(
                str(model_metadata["config_source_model_name"])
                if model_metadata.get("config_source_model_name") is not None
                else "profile"
            ),
            config_source_hf_model_id=(
                str(model_metadata["config_source_hf_model_id"])
                if model_metadata.get("config_source_hf_model_id") is not None
                else "profile"
            ),
            router_reason_code=router_reason_code,
            policy_schema_version=self._policy_bundle.policy.policy_schema_version,
            policy_version=self._policy_bundle.policy.policy_version,
            policy_hash=self._policy_bundle.policy_hash,
            decision_engine_version=self._gov.decision_engine_version,
            governance_decisions=state.decisions,
            tool_calls=state.tool_calls,
            handoffs=state.handoffs,
            memory_writes=state.memory_writes,
            approval_status=state.approval_status,
            redaction_mode="audit",
            privacy_mode=self._config.privacy_mode,
        )
        payload = self.audit_redact(record.model_dump(mode="json"))
        path = self._audit_dir / f"{run_id}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def decide_approval(
        self,
        *,
        approval_id: str,
        approve: bool,
        actor: str,
        reason: str | None,
    ) -> ApprovalDecisionResult:
        return self._approval_store.decide(
            approval_id=approval_id,
            approve=approve,
            actor=actor,
            reason=reason,
        )

    def execute_approval(self, *, approval_id: str) -> ApprovalDecisionResult:
        return self._approval_store.mark_executed(approval_id=approval_id)

    def _record_decision(self, run_id: str, decision: GovernanceDecision) -> None:
        state = self._runs.setdefault(run_id, GovernanceRunState())
        state.decisions.append(decision)

    def _record_tool_call(self, run_id: str, tool_call: ToolCallRecord) -> None:
        state = self._runs.setdefault(run_id, GovernanceRunState())
        state.tool_calls.append(tool_call)

    def _record_handoff(self, run_id: str, handoff: HandoffCallRecord) -> None:
        state = self._runs.setdefault(run_id, GovernanceRunState())
        state.handoffs.append(handoff)

    def _record_memory_write(self, run_id: str, memory_write: MemoryWriteRecord) -> None:
        state = self._runs.setdefault(run_id, GovernanceRunState())
        state.memory_writes.append(memory_write)

    def _set_approval_status(self, run_id: str, status: str) -> None:
        state = self._runs.setdefault(run_id, GovernanceRunState())
        state.approval_status = status

    def _default_allow_decision(self, *, phase: GovernancePhase, target: str) -> GovernanceDecision:
        return GovernanceDecision(
            phase=phase,
            target=target,
            action=GovernanceAction.ALLOW,
            reason_code="RULE_ROUTE",
            matched_rule_path=None,
            policy_schema_version="disabled",
            policy_version="disabled",
            policy_hash="disabled",
            decision_engine_version=self._gov.decision_engine_version,
            explain="governance disabled",
        )

    @staticmethod
    def _hash_payload(payload: Any) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_governance_runtime(config: RuntimeConfig) -> GovernanceRuntime | None:
    gov_cfg = config.governance
    if not gov_cfg.enabled:
        return None
    return GovernanceRuntime(config=config)


def governance_startup_abort(
    config: RuntimeConfig,
    runtime: GovernanceRuntime | None,
) -> str | None:
    if runtime is None:
        return None
    err = runtime.execution_startup_error()
    if err is None:
        return None
    if config.governance.policy_fail_mode == "fail_closed":
        return err
    return None


def default_governance_policy_path(profile_name: str) -> str:
    return str(Path("config") / "policies" / f"{profile_name}.toml")


def ensure_governance_defaults(config: GovernanceConfig, *, profile_name: str) -> GovernanceConfig:
    if config.policy_path:
        return config
    return config.model_copy(update={"policy_path": default_governance_policy_path(profile_name)})
