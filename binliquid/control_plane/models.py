from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        use_enum_values=True,
    )


class RuntimeKind(StrEnum):
    BINLIQUID_CORE = "binliquid_core"
    BINLIQUID_TEAM = "binliquid_team"
    EXTERNAL_STDIO = "external_stdio"
    EXTERNAL_HTTP = "external_http"
    COMPUTER_USE_ADAPTER = "computer_use_adapter"


class ExecutionSurface(StrEnum):
    CORE_RUNTIME = "core_runtime"
    TEAM_RUNTIME = "team_runtime"
    EXTERNAL_STDIO = "external_stdio"
    COMPUTER_USE_LIVE = "computer_use_live"
    OPERATOR_PANEL = "operator_panel"


class RiskClass(StrEnum):
    READ_ONLY = "read_only"
    LOCAL_WRITE = "local_write"
    EXTERNAL_WRITE = "external_write"
    MUTATION = "mutation"
    DESTRUCTIVE = "destructive"
    CREDENTIAL_SENSITIVE = "credential_sensitive"
    FINANCIAL_OR_LEGAL = "financial_or_legal"
    SECURITY_SENSITIVE = "security_sensitive"
    COMPUTER_USE_VISUAL = "computer_use_visual"
    UNKNOWN = "unknown"


class ControlPlaneDecisionAction(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    UNKNOWN = "unknown"


class AgentStatus(StrEnum):
    REGISTERED = "registered"
    DISABLED = "disabled"
    BLOCKED = "blocked"


class AgentReadiness(StrEnum):
    NOT_EVALUATED = "not_evaluated"
    POLICY_SIMULATED = "policy_simulated"
    QUALIFIED = "qualified"
    PRODUCTION_ALLOWED = "production_allowed"
    BLOCKED = "blocked"


class RunStatus(StrEnum):
    CREATED = "created"
    POLICY_EVALUATING = "policy_evaluating"
    POLICY_BLOCKED = "policy_blocked"
    APPROVAL_PENDING = "approval_pending"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVED = "approved"
    EXECUTING = "executing"
    BLOCKED = "blocked"
    FAILED = "failed"
    COMPLETED = "completed"
    EVIDENCE_EXPORTED = "evidence_exported"
    VERIFIED = "verified"


class ClaimStatus(StrEnum):
    ALLOWED = "allowed"
    CONDITIONAL = "conditional"
    BLOCKED = "blocked"
    DEFERRED = "deferred"


class AgentOwner(StrictModel):
    team: str
    contact: str


class AgentQualification(StrictModel):
    required: bool = True
    minimum_level: Literal["development", "pilot", "enterprise", "ga"] = "pilot"
    status: Literal["missing", "development", "pilot", "enterprise", "ga"] = "missing"


class AgentEvidenceRequirements(StrictModel):
    signed_pack_required: bool = True
    replay_required: bool = True


class DeclaredAction(StrictModel):
    action_id: str
    phase: Literal["task", "tool", "handoff", "memory_write", "device_action"] = "tool"
    risk_class: RiskClass
    target_kind: str
    effect: str
    action_type: str = "control_plane_action"

    @field_validator("action_id")
    @classmethod
    def _action_id_valid(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,127}", value):
            raise ValueError("action_id must be stable lowercase snake/kebab text")
        return value


class AgentSpec(StrictModel):
    version: Literal["control-plane.agent/v1"]
    agent_id: str
    display_name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    runtime_kind: RuntimeKind
    profile: str = "enterprise"
    policy_profile: str | None = None
    owner: AgentOwner
    allowed_surfaces: list[ExecutionSurface] = Field(default_factory=list)
    blocked_surfaces: list[ExecutionSurface] = Field(default_factory=list)
    declared_actions: list[DeclaredAction] = Field(default_factory=list)
    qualification: AgentQualification = Field(default_factory=AgentQualification)
    evidence: AgentEvidenceRequirements = Field(default_factory=AgentEvidenceRequirements)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("agent_id")
    @classmethod
    def _agent_id_valid(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}[a-z0-9]", value):
            raise ValueError("agent_id must be kebab-case and 3-64 chars")
        return value

    @model_validator(mode="after")
    def _set_policy_and_validate_surfaces(self) -> AgentSpec:
        if self.policy_profile is None:
            self.policy_profile = self.profile
        overlap = set(self.allowed_surfaces) & set(self.blocked_surfaces)
        if overlap:
            values = ", ".join(sorted(str(item) for item in overlap))
            raise ValueError(f"allowed_surfaces and blocked_surfaces overlap: {values}")
        return self


class AgentRecord(StrictModel):
    version: Literal["control-plane.agent-record/v1"] = "control-plane.agent-record/v1"
    agent_id: str
    spec_hash: str
    status: AgentStatus = AgentStatus.REGISTERED
    readiness: AgentReadiness = AgentReadiness.NOT_EVALUATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    disabled_reason: str | None = None
    last_run_id: str | None = None
    last_evidence_pack_id: str | None = None
    spec: AgentSpec


class AgentRegisterResult(StrictModel):
    status: Literal["registered", "unchanged"]
    agent_id: str
    spec_hash: str
    record_path: str
    record: AgentRecord


class ActionProposal(StrictModel):
    version: Literal["control-plane.action-proposal/v1"]
    correlation_id: str
    run_id: str
    agent_id: str
    phase: Literal["task", "tool", "handoff", "memory_write", "device_action"] = "tool"
    action_id: str
    action_type: str = "control_plane_action"
    target_kind: str
    target_ref: str = ""
    risk_class: RiskClass = RiskClass.UNKNOWN
    effect_summary: str
    args_fingerprint: str = "sha256:unknown"
    idempotency_key: str
    payload_redacted: bool = True
    requested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ControlPlanePolicyDecision(StrictModel):
    action_id: str
    phase: str
    risk_class: RiskClass
    decision_action: ControlPlaneDecisionAction
    reason_code: str
    matched_rule_path: str
    policy_hash: str
    approval_id: str | None = None
    qualification_required: bool = False


class PolicySimulationSummary(StrictModel):
    allow: int = 0
    require_approval: int = 0
    deny: int = 0
    unknown: int = 0


class PolicySimulationResult(StrictModel):
    version: Literal["control-plane.policy-simulation/v1"] = (
        "control-plane.policy-simulation/v1"
    )
    agent_id: str
    policy_hash: str
    overall_status: Literal["pass", "conditional", "blocked"]
    summary: PolicySimulationSummary
    decisions: list[ControlPlanePolicyDecision] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)


class ControlPlaneRunSummary(StrictModel):
    version: Literal["control-plane.run/v1"] = "control-plane.run/v1"
    run_id: str
    agent_id: str
    profile: str
    status: RunStatus
    submitted_by: str
    identity_ref: str | None = None
    input_hash: str
    policy_hash: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    approval_ids: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    evidence_pack_id: str | None = None
    blocking_reasons: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class EvidencePackItem(StrictModel):
    kind: str
    path: str
    sha256: str
    required: bool = True


class RedactionSummary(StrictModel):
    raw_screenshots_persisted: int = 0
    secrets_redacted: bool = True
    pii_redaction_enabled: bool = True


class EvidenceVerificationSummary(StrictModel):
    hash_chain_verified: bool = False
    signature_verified: bool = False
    replay_verified: bool = False


class EvidenceSignatureSummary(StrictModel):
    mode: str = "unsigned"
    key_id: str | None = None
    algorithm: str = "ed25519"
    signature_ref: str | None = None


class EvidencePackManifest(StrictModel):
    version: Literal["control-plane.evidence-pack/v1"] = "control-plane.evidence-pack/v1"
    pack_id: str
    run_id: str
    agent_id: str
    profile: str
    runtime_version: str
    git_commit: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    items: list[EvidencePackItem] = Field(default_factory=list)
    redaction_summary: RedactionSummary = Field(default_factory=RedactionSummary)
    verification: EvidenceVerificationSummary = Field(
        default_factory=EvidenceVerificationSummary
    )
    signature: EvidenceSignatureSummary = Field(default_factory=EvidenceSignatureSummary)
    warnings: list[str] = Field(default_factory=list)


class EvidenceVerifyResult(StrictModel):
    status: Literal["pass", "fail"]
    hash_chain_verified: bool
    signature_verified: bool
    required_items_present: bool
    replay_verified: bool
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ClaimItem(StrictModel):
    claim_id: str
    status: ClaimStatus
    required_evidence: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)


class ClaimMatrix(StrictModel):
    version: Literal["control-plane.claim-matrix/v1"] = "control-plane.claim-matrix/v1"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    claims: list[ClaimItem] = Field(default_factory=list)


class ReadinessReport(StrictModel):
    version: Literal["control-plane.readiness/v1"] = "control-plane.readiness/v1"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    profile: str
    status: Literal["pass", "conditional", "blocked"]
    checks: dict[str, bool] = Field(default_factory=dict)
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
