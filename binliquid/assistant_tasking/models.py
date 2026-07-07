from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator

from binliquid.memory.models import StrictModel


class AssistantTaskIntentKind(StrEnum):
    ASK_HOW_TO = "ask_how_to"
    PLAN_AGENT_TASK = "plan_agent_task"
    SUBMIT_AGENT_TASK = "submit_agent_task"
    EXPLAIN_RUN = "explain_run"
    UNSUPPORTED_DESTRUCTIVE = "unsupported_destructive"
    CLARIFICATION_REQUIRED = "clarification_required"


class AssistantTaskRiskClass(StrEnum):
    READ_ONLY = "read_only"
    EXTERNAL_WRITE = "external_write"
    MUTATION = "mutation"
    DESTRUCTIVE = "destructive"
    CREDENTIAL_SENSITIVE = "credential_sensitive"
    UNKNOWN = "unknown"


class AssistantTaskPolicyDecision(StrEnum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"
    UNKNOWN = "unknown"


class AssistantTaskPlanStatus(StrEnum):
    PLANNED = "planned"
    BLOCKED = "blocked"
    CLARIFICATION_REQUIRED = "clarification_required"


class AssistantTaskSubmitStatus(StrEnum):
    ACCEPTED = "accepted"
    BLOCKED_PENDING_APPROVAL = "blocked_pending_approval"
    DENIED = "denied"
    INVALID_REQUEST = "invalid_request"
    UNKNOWN_AGENT = "unknown_agent"


class AgentTaskCandidate(StrictModel):
    agent_id: str = Field(alias="agentId")
    label: str
    enrolled: bool
    workspace_id: str | None = Field(default=None, alias="workspaceId")
    principal_id: str | None = Field(default=None, alias="principalId")
    allowed_surfaces: tuple[str, ...] = Field(default=(), alias="allowedSurfaces")
    blocked_surfaces: tuple[str, ...] = Field(default=(), alias="blockedSurfaces")
    declared_actions: tuple[str, ...] = Field(default=(), alias="declaredActions")
    qualification_status: str = Field(default="unknown", alias="qualificationStatus")
    blocking_reasons: tuple[str, ...] = Field(default=(), alias="blockingReasons")


class PolicyPreview(StrictModel):
    decision: AssistantTaskPolicyDecision
    risk_class: AssistantTaskRiskClass = Field(alias="riskClass")
    approval_required: bool = Field(alias="approvalRequired")
    safe_to_submit: bool = Field(alias="safeToSubmit")
    reason_code: str = Field(alias="reasonCode")
    blocked_reasons: tuple[str, ...] = Field(default=(), alias="blockedReasons")


class EvidenceExpectation(StrictModel):
    mode: Literal["hash_only_redacted"] = "hash_only_redacted"
    expected_refs: tuple[str, ...] = Field(default=(), alias="expectedRefs")
    raw_content_persisted: bool = Field(default=False, alias="rawContentPersisted")


class AssistantTaskPlanRequest(StrictModel):
    schema_version: Literal["assistant-tasking.plan-request/v1"] = Field(
        default="assistant-tasking.plan-request/v1",
        alias="schemaVersion",
    )
    profile: str = "enterprise"
    message: str = Field(min_length=1, max_length=4000)
    operator_id: str = Field(default="operator-local", alias="operatorId")
    workspace_id: str = Field(default="pilot-workspace", alias="workspaceId")
    agent_hint: str | None = Field(default=None, alias="agentHint")
    root_dir: str = Field(default=".binliquid/control-plane", alias="rootDir")


class AssistantTaskPlan(StrictModel):
    schema_version: Literal["assistant-tasking.plan/v1"] = Field(
        default="assistant-tasking.plan/v1",
        alias="schemaVersion",
    )
    proposal_id: str = Field(alias="proposalId")
    plan_hash: str = Field(alias="planHash")
    status: AssistantTaskPlanStatus
    intent_kind: AssistantTaskIntentKind = Field(alias="intentKind")
    selected_agent: AgentTaskCandidate | None = Field(default=None, alias="selectedAgent")
    candidate_agents: tuple[AgentTaskCandidate, ...] = Field(default=(), alias="candidateAgents")
    task_summary: str = Field(alias="taskSummary")
    risk_class: AssistantTaskRiskClass = Field(alias="riskClass")
    policy_preview: PolicyPreview = Field(alias="policyPreview")
    approval_required: bool = Field(alias="approvalRequired")
    submit_mode: Literal["proposal_first", "disabled_with_reason"] = Field(alias="submitMode")
    idempotency_key: str = Field(alias="idempotencyKey")
    evidence_expectation: EvidenceExpectation = Field(alias="evidenceExpectation")
    safe_to_submit: bool = Field(alias="safeToSubmit")
    blocked_reasons: tuple[str, ...] = Field(default=(), alias="blockedReasons")
    source_refs: tuple[str, ...] = Field(default=(), alias="sourceRefs")
    created_at_utc: str = Field(alias="createdAtUtc")

    @field_validator("plan_hash")
    @classmethod
    def _plan_hash_valid(cls, value: str) -> str:
        if not value.startswith("sha256:") or len(value) != 71:
            raise ValueError("plan_hash must be sha256:<64 hex chars>")
        return value


class AssistantTaskSubmissionRequest(StrictModel):
    schema_version: Literal["assistant-tasking.submit-request/v1"] = Field(
        default="assistant-tasking.submit-request/v1",
        alias="schemaVersion",
    )
    proposal_id: str = Field(alias="proposalId")
    confirm_plan_hash: str = Field(alias="confirmPlanHash")
    operator_id: str = Field(alias="operatorId")
    root_dir: str = Field(default=".binliquid/control-plane", alias="rootDir")
    profile: str = "enterprise"


class AssistantTaskSubmissionResult(StrictModel):
    schema_version: Literal["assistant-tasking.submission/v1"] = Field(
        default="assistant-tasking.submission/v1",
        alias="schemaVersion",
    )
    proposal_id: str = Field(alias="proposalId")
    plan_hash: str = Field(alias="planHash")
    status: AssistantTaskSubmitStatus
    policy_decision: AssistantTaskPolicyDecision = Field(alias="policyDecision")
    reason_code: str = Field(alias="reasonCode")
    run_id: str | None = Field(default=None, alias="runId")
    approval_id: str | None = Field(default=None, alias="approvalId")
    evidence_ref: str | None = Field(default=None, alias="evidenceRef")
    replay_status: str | None = Field(default=None, alias="replayStatus")
    idempotency_status: str | None = Field(default=None, alias="idempotencyStatus")
    blocked_reasons: tuple[str, ...] = Field(default=(), alias="blockedReasons")
    next_actions: tuple[str, ...] = Field(default=(), alias="nextActions")
    generated_at_utc: str = Field(alias="generatedAtUtc")


class AssistantTaskStatus(StrictModel):
    schema_version: Literal["assistant-tasking.status/v1"] = Field(
        default="assistant-tasking.status/v1",
        alias="schemaVersion",
    )
    proposal_id: str = Field(alias="proposalId")
    status: str
    plan: AssistantTaskPlan | None = None
    submission: AssistantTaskSubmissionResult | None = None
    evidence_refs: tuple[str, ...] = Field(default=(), alias="evidenceRefs")
    blocking_reasons: tuple[str, ...] = Field(default=(), alias="blockingReasons")


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_payload(payload: object) -> str:
    import json

    return "sha256:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
