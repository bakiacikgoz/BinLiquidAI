from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from binliquid.control_plane.models import ControlPlanePolicyDecision, StrictModel


class ExternalActionRequest(StrictModel):
    version: Literal["control-plane.external-action-request/v1"] = (
        "control-plane.external-action-request/v1"
    )
    request_id: str = Field(alias="requestId")
    agent_id: str = Field(alias="agentId")
    actor_id: str = Field(alias="actorId")
    intent: str = Field(min_length=1, max_length=500)
    action_kind: Literal[
        "read",
        "mutate",
        "external_write",
        "destructive",
        "credential_sensitive",
        "unknown",
    ] = Field(alias="actionKind")
    target_ref: str | None = Field(default=None, alias="targetRef")
    payload_hash: str = Field(alias="payloadHash")
    payload_redaction_summary: dict[str, Any] = Field(
        default_factory=dict,
        alias="payloadRedactionSummary",
    )
    requested_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        alias="requestedAt",
    )
    dry_run: bool = Field(default=True, alias="dryRun")

    @field_validator("request_id")
    @classmethod
    def _request_id_valid(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{2,127}", value):
            raise ValueError("request_id must be a stable external idempotency key")
        return value

    @field_validator("agent_id")
    @classmethod
    def _agent_id_valid(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}[a-z0-9]", value):
            raise ValueError("agent_id must be kebab-case and 3-64 chars")
        return value

    @field_validator("payload_hash")
    @classmethod
    def _payload_hash_valid(cls, value: str) -> str:
        if not re.fullmatch(r"sha256:[a-fA-F0-9]{64}", value):
            raise ValueError("payload_hash must be sha256:<64 hex chars>")
        return value.lower()


class ExternalActionResponse(StrictModel):
    version: Literal["control-plane.external-action-response/v1"] = (
        "control-plane.external-action-response/v1"
    )
    request_id: str = Field(alias="requestId")
    agent_id: str = Field(alias="agentId")
    status: Literal[
        "accepted",
        "requires_approval",
        "blocked_pending_approval",
        "denied",
        "invalid_request",
        "unknown_agent",
    ]
    reason_code: str = Field(alias="reasonCode")
    policy_decision: ControlPlanePolicyDecision | None = Field(
        default=None,
        alias="policyDecision",
    )
    run_id: str | None = Field(default=None, alias="runId")
    approval_id: str | None = Field(default=None, alias="approvalId")
    evidence_ref: str | None = Field(default=None, alias="evidenceRef")
    dry_run: bool = Field(alias="dryRun")
    next_actions: list[str] = Field(default_factory=list, alias="nextActions")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        alias="generatedAt",
    )
