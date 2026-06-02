from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from binliquid import __version__
from binliquid.control_plane.errors import ControlPlaneError
from binliquid.control_plane.external_contracts import (
    ExternalActionRequest,
    ExternalActionResponse,
)
from binliquid.control_plane.models import (
    ActionProposal,
    AgentReadiness,
    AgentStatus,
    ControlPlaneDecisionAction,
    ControlPlaneRunSummary,
    RiskClass,
    RunStatus,
)
from binliquid.control_plane.policy_simulator import PolicySimulator
from binliquid.control_plane.registry import AgentRegistry
from binliquid.control_plane.storage import ControlPlaneStore, canonical_json_hash
from binliquid.governance.approval_store import ApprovalStore
from binliquid.runtime.config import RuntimeConfig

EXTERNAL_GATEWAY_CONTRACT_VERSION = "control-plane.external-gateway/v1"
EXTERNAL_RUNTIME_KINDS = {"external_stdio", "external_http"}
SENSITIVE_REDACTION_KEYS = {"secret", "token", "password", "private_key", "api_key"}


class ExternalAgentGateway:
    def __init__(
        self,
        *,
        config: RuntimeConfig,
        registry: AgentRegistry,
        root_dir: str | Path = ".binliquid/control-plane",
    ):
        self.config = config
        self.registry = registry
        self.store = ControlPlaneStore(root_dir)
        self.policy = PolicySimulator(config=config)
        self.approvals = ApprovalStore(config.governance.approval_store_path)

    def submit_action(self, request: ExternalActionRequest) -> ExternalActionResponse:
        run_id = _gateway_run_id(request.request_id)
        evidence_ref = f"external-gateway/evidence/{request.request_id}.json"
        try:
            record = self.registry.get(request.agent_id)
        except ControlPlaneError:
            response = ExternalActionResponse(
                request_id=request.request_id,
                agent_id=request.agent_id,
                status="unknown_agent",
                reason_code="UNKNOWN_AGENT",
                dry_run=request.dry_run,
                evidence_ref=evidence_ref,
                next_actions=["agent.register"],
            )
            self._write_evidence(request=request, response=response, run_id=None)
            return response

        if str(record.status) != AgentStatus.REGISTERED.value:
            response = ExternalActionResponse(
                request_id=request.request_id,
                agent_id=request.agent_id,
                status="denied",
                reason_code="AGENT_DISABLED",
                dry_run=request.dry_run,
                evidence_ref=evidence_ref,
                next_actions=["agent.show", "agent.enable"],
            )
            self._write_evidence(request=request, response=response, run_id=None)
            return response

        if str(record.spec.runtime_kind) not in EXTERNAL_RUNTIME_KINDS:
            response = ExternalActionResponse(
                request_id=request.request_id,
                agent_id=request.agent_id,
                status="denied",
                reason_code="AGENT_RUNTIME_NOT_EXTERNAL",
                dry_run=request.dry_run,
                evidence_ref=evidence_ref,
                next_actions=["agent.register_external"],
            )
            self._write_evidence(request=request, response=response, run_id=None)
            return response

        if not _redaction_summary_safe(request.payload_redaction_summary):
            response = ExternalActionResponse(
                request_id=request.request_id,
                agent_id=request.agent_id,
                status="invalid_request",
                reason_code="PAYLOAD_REDACTION_UNSAFE",
                dry_run=request.dry_run,
                evidence_ref=evidence_ref,
                next_actions=["redact.payload", "retry"],
            )
            self._write_evidence(request=request, response=response, run_id=None)
            return response

        proposal = _proposal_from_request(request=request, run_id=run_id)
        decision = self.policy.simulate_action(proposal)
        request_hash = canonical_json_hash(request.model_dump(mode="json", by_alias=True))
        status = RunStatus.CREATED
        approval_id: str | None = None
        response_status = "accepted"
        next_actions = ["evidence.inspect"]

        if decision.decision_action == ControlPlaneDecisionAction.DENY:
            status = RunStatus.POLICY_BLOCKED
            response_status = "denied"
            next_actions = ["policy.review", "request.update"]
        elif decision.decision_action == ControlPlaneDecisionAction.REQUIRE_APPROVAL:
            if request.dry_run:
                response_status = "requires_approval"
                next_actions = ["gateway.submit --dry-run false", "approval.required"]
            else:
                ticket = self.approvals.create_ticket(
                    run_id=run_id,
                    target_kind="external_agent_action",
                    target_ref=f"{request.agent_id}:{request.action_kind}",
                    action_hash=canonical_json_hash(proposal.model_dump(mode="json")),
                    policy_hash=decision.policy_hash,
                    request_hash=request_hash,
                    snapshot_hash=canonical_json_hash(
                        {
                            "request": request.model_dump(mode="json", by_alias=True),
                            "decision": decision.model_dump(mode="json"),
                        }
                    ),
                    snapshot={
                        "kind": "external_agent_action",
                        "contract_version": EXTERNAL_GATEWAY_CONTRACT_VERSION,
                        "request": request.model_dump(mode="json", by_alias=True),
                        "decision": decision.model_dump(mode="json"),
                        "runtime_version": __version__,
                    },
                    ttl_seconds=self.config.governance.approval_ttl_seconds,
                    idempotency_key=f"external-gateway:{request.request_id}",
                )
                approval_id = ticket.approval_id
                status = RunStatus.APPROVAL_PENDING
                response_status = "blocked_pending_approval"
                next_actions = ["approval.show", "approval.decide", "approval.execute"]
        else:
            status = RunStatus.COMPLETED
            next_actions = ["evidence.inspect", "evidence.verify"]

        summary = ControlPlaneRunSummary(
            run_id=run_id,
            agent_id=request.agent_id,
            profile=self.config.profile_name,
            status=status,
            submitted_by=f"external:{request.actor_id}",
            identity_ref=f"external:{request.actor_id}",
            input_hash=request_hash,
            policy_hash=decision.policy_hash,
            completed_at=datetime.now(UTC) if status == RunStatus.COMPLETED else None,
            approval_ids=[approval_id] if approval_id else [],
            artifact_refs=[evidence_ref],
            evidence_pack_id=None,
            blocking_reasons=[decision.reason_code] if status == RunStatus.POLICY_BLOCKED else [],
            next_actions=next_actions,
        )
        self._write_run(
            summary=summary,
            request=request,
            proposal=proposal,
            decision=decision.model_dump(mode="json"),
        )
        self.registry.update_record(
            record.model_copy(
                update={
                    "readiness": AgentReadiness.POLICY_SIMULATED,
                    "last_run_id": run_id,
                    "updated_at": datetime.now(UTC),
                }
            )
        )

        response = ExternalActionResponse(
            request_id=request.request_id,
            agent_id=request.agent_id,
            status=response_status,
            reason_code=decision.reason_code,
            policy_decision=decision,
            run_id=run_id,
            approval_id=approval_id,
            evidence_ref=evidence_ref,
            dry_run=request.dry_run,
            next_actions=next_actions,
        )
        self._write_evidence(request=request, response=response, run_id=run_id)
        return response

    def _write_run(
        self,
        *,
        summary: ControlPlaneRunSummary,
        request: ExternalActionRequest,
        proposal: ActionProposal,
        decision: dict[str, Any],
    ) -> None:
        self.store.write_json_atomic(
            f"runs/{summary.run_id}.json",
            {
                "version": "control-plane.external-run-state/v1",
                "run": summary.model_dump(mode="json"),
                "external_request": request.model_dump(mode="json", by_alias=True),
                "action_proposal": proposal.model_dump(mode="json"),
                "policy_decision": decision,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )

    def _write_evidence(
        self,
        *,
        request: ExternalActionRequest,
        response: ExternalActionResponse,
        run_id: str | None,
    ) -> None:
        self.store.write_json_atomic(
            f"external-gateway/evidence/{request.request_id}.json",
            {
                "version": "control-plane.external-gateway-evidence/v1",
                "request_id": request.request_id,
                "agent_id": request.agent_id,
                "run_id": run_id,
                "request": {
                    "actorId": request.actor_id,
                    "intent": request.intent,
                    "actionKind": request.action_kind,
                    "targetRef": request.target_ref,
                    "payloadHash": request.payload_hash,
                    "payloadRedactionSummary": request.payload_redaction_summary,
                    "requestedAt": request.requested_at.isoformat(),
                    "dryRun": request.dry_run,
                },
                "response": response.model_dump(mode="json", by_alias=True),
                "request_hash": canonical_json_hash(
                    request.model_dump(mode="json", by_alias=True)
                ),
                "response_hash": canonical_json_hash(
                    response.model_dump(mode="json", by_alias=True)
                ),
                "generated_at": datetime.now(UTC).isoformat(),
            },
        )


def submit_external_action_file(
    *,
    path: str | Path,
    config: RuntimeConfig,
    registry: AgentRegistry,
    root_dir: str | Path = ".binliquid/control-plane",
) -> ExternalActionResponse:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        request = ExternalActionRequest.model_validate(payload)
    except (json.JSONDecodeError, OSError, ValidationError) as exc:
        _ = exc
        return ExternalActionResponse(
            request_id="invalid",
            agent_id="unknown",
            status="invalid_request",
            reason_code="EXTERNAL_ACTION_CONTRACT_INVALID",
            dry_run=True,
            next_actions=["fix.request.schema"],
            evidence_ref=None,
        )
    return ExternalAgentGateway(
        config=config,
        registry=registry,
        root_dir=root_dir,
    ).submit_action(request)


def _proposal_from_request(*, request: ExternalActionRequest, run_id: str) -> ActionProposal:
    return ActionProposal(
        version="control-plane.action-proposal/v1",
        correlation_id=request.request_id,
        run_id=run_id,
        agent_id=request.agent_id,
        phase="tool",
        action_id=f"external_{request.action_kind}",
        action_type="external_agent_action",
        target_kind=request.action_kind,
        target_ref=request.target_ref or "",
        risk_class=_risk_for_action_kind(request.action_kind),
        effect_summary=request.intent,
        args_fingerprint=request.payload_hash,
        idempotency_key=request.request_id,
        payload_redacted=True,
        requested_at=request.requested_at,
    )


def _risk_for_action_kind(action_kind: str) -> RiskClass:
    return {
        "read": RiskClass.READ_ONLY,
        "mutate": RiskClass.MUTATION,
        "external_write": RiskClass.EXTERNAL_WRITE,
        "destructive": RiskClass.DESTRUCTIVE,
        "credential_sensitive": RiskClass.CREDENTIAL_SENSITIVE,
        "unknown": RiskClass.UNKNOWN,
    }.get(action_kind, RiskClass.UNKNOWN)


def _redaction_summary_safe(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in SENSITIVE_REDACTION_KEYS):
                return False
            if not _redaction_summary_safe(nested):
                return False
        return True
    if isinstance(value, list):
        return all(_redaction_summary_safe(item) for item in value)
    if isinstance(value, str):
        lowered = value.lower()
        return not any(marker in lowered for marker in SENSITIVE_REDACTION_KEYS)
    return True


def _gateway_run_id(request_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in request_id)
    return f"cp-ext-run-{safe[:72]}"
