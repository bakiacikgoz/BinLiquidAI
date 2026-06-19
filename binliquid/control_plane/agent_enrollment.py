from __future__ import annotations

import secrets
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from binliquid.control_plane.enterprise_workspace import (
    SHA256_HEX_RE,
    StrictModel,
    _validate_optional_hash,
    _validate_safe_id,
    sha256_text,
)


class EnrollmentMemoryScope(StrictModel):
    scope: str = Field(min_length=1, max_length=80)
    mode: Literal["read", "write", "proposal_only", "requires_approval"]


class AgentEnrollmentToken(StrictModel):
    schema_version: Literal["agent-enrollment-token/v1"] = Field(
        default="agent-enrollment-token/v1",
        alias="schemaVersion",
    )
    token_id: str = Field(alias="tokenId")
    token_hash: str = Field(alias="tokenHash")
    organization_id: str = Field(alias="organizationId")
    workspace_id: str = Field(alias="workspaceId")
    intended_agent_id: str | None = Field(default=None, alias="intendedAgentId")
    intended_device_label: str = Field(alias="intendedDeviceLabel", min_length=1, max_length=160)
    allowed_principal_type: Literal["service_agent", "external_agent"] = Field(
        alias="allowedPrincipalType"
    )
    allowed_capabilities: tuple[str, ...] = Field(alias="allowedCapabilities")
    policy_profile: str = Field(alias="policyProfile", min_length=1)
    memory_scopes: tuple[EnrollmentMemoryScope, ...] = Field(default_factory=tuple, alias="memoryScopes")
    created_by_principal_id: str = Field(alias="createdByPrincipalId")
    created_at_utc: datetime = Field(alias="createdAtUtc")
    expires_at_utc: datetime = Field(alias="expiresAtUtc")
    max_uses: Literal[1] = Field(default=1, alias="maxUses")
    use_count: int = Field(default=0, ge=0, le=1, alias="useCount")
    status: Literal["active", "used", "revoked", "expired"] = "active"
    approval_required: Literal[True] = Field(default=True, alias="approvalRequired")

    @field_validator(
        "token_id",
        "organization_id",
        "workspace_id",
        "intended_agent_id",
        "created_by_principal_id",
    )
    @classmethod
    def _safe_ids(cls, value: str | None, info: object) -> str | None:
        if value is None:
            return None
        return _validate_safe_id(value, str(getattr(info, "field_name", "id")))

    @field_validator("token_hash")
    @classmethod
    def _token_hash(cls, value: str) -> str:
        if not SHA256_HEX_RE.fullmatch(value):
            raise ValueError("token_hash must be sha256 hex")
        return value

    @field_validator("allowed_capabilities")
    @classmethod
    def _capabilities(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        capabilities = tuple(sorted(set(value)))
        if not capabilities:
            raise ValueError("allowed_capabilities cannot be empty")
        for capability in capabilities:
            _validate_safe_id(capability, "capability")
        return capabilities


class AgentEnrollmentTokenCreateRequest(StrictModel):
    workspace_id: str = Field(alias="workspaceId")
    intended_agent_id: str | None = Field(default=None, alias="intendedAgentId")
    intended_device_label: str = Field(alias="intendedDeviceLabel", min_length=1, max_length=160)
    allowed_principal_type: Literal["service_agent", "external_agent"] = Field(
        default="external_agent",
        alias="allowedPrincipalType",
    )
    allowed_capabilities: tuple[str, ...] = Field(alias="allowedCapabilities")
    ttl_minutes: int = Field(default=15, ge=1, le=1440, alias="ttlMinutes")


class AgentEnrollmentTokenCreateResult(StrictModel):
    schema_version: Literal["agent-enrollment-token-create-result/v1"] = Field(
        default="agent-enrollment-token-create-result/v1",
        alias="schemaVersion",
    )
    status: Literal["created", "blocked"]
    token_id: str | None = Field(default=None, alias="tokenId")
    raw_token: str | None = Field(default=None, alias="rawToken")
    expires_at_utc: datetime | None = Field(default=None, alias="expiresAtUtc")
    evidence_ref: str | None = Field(default=None, alias="evidenceRef")
    raw_token_shown_once: bool = Field(default=False, alias="rawTokenShownOnce")
    raw_token_persisted: Literal[False] = Field(default=False, alias="rawTokenPersisted")
    blocking_reasons: list[str] = Field(default_factory=list, alias="blockingReasons")


class AgentEnrollmentTokenRevokeResult(StrictModel):
    schema_version: Literal["agent-enrollment-token-revoke-result/v1"] = Field(
        default="agent-enrollment-token-revoke-result/v1",
        alias="schemaVersion",
    )
    status: Literal["revoked", "unchanged", "blocked"]
    token_id: str = Field(alias="tokenId")
    evidence_ref: str | None = Field(default=None, alias="evidenceRef")
    blocking_reasons: list[str] = Field(default_factory=list, alias="blockingReasons")


class AgentEnrollmentRequest(StrictModel):
    schema_version: Literal["agent-enrollment-request/v1"] = Field(
        default="agent-enrollment-request/v1",
        alias="schemaVersion",
    )
    request_id: str = Field(alias="requestId")
    token_id: str = Field(alias="tokenId")
    token_proof_hash: str = Field(alias="tokenProofHash")
    workspace_id: str = Field(alias="workspaceId")
    agent_id: str = Field(alias="agentId")
    agent_display_name: str = Field(alias="agentDisplayName", min_length=1, max_length=160)
    device_display_name: str = Field(alias="deviceDisplayName", min_length=1, max_length=160)
    platform: Literal["linux", "macos", "windows", "unknown"]
    capabilities: tuple[str, ...]
    host_fingerprint_hash: str | None = Field(default=None, alias="hostFingerprintHash")
    requested_at_utc: datetime = Field(alias="requestedAtUtc")
    status: Literal["pending_approval", "approved", "rejected", "expired"] = "pending_approval"
    idempotency_key: str = Field(alias="idempotencyKey", min_length=8, max_length=160)

    @field_validator("request_id", "token_id", "workspace_id", "agent_id")
    @classmethod
    def _safe_ids(cls, value: str, info: object) -> str:
        return _validate_safe_id(value, str(getattr(info, "field_name", "id")))

    @field_validator("token_proof_hash")
    @classmethod
    def _proof_hash(cls, value: str) -> str:
        if not SHA256_HEX_RE.fullmatch(value):
            raise ValueError("token_proof_hash must be sha256 hex")
        return value

    @field_validator("host_fingerprint_hash")
    @classmethod
    def _host_hash(cls, value: str | None) -> str | None:
        return _validate_optional_hash(value, "host_fingerprint_hash")

    @field_validator("capabilities")
    @classmethod
    def _capabilities(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        capabilities = tuple(sorted(set(value)))
        if not capabilities:
            raise ValueError("capabilities cannot be empty")
        for capability in capabilities:
            _validate_safe_id(capability, "capability")
        return capabilities


class AgentEnrollmentImportResult(StrictModel):
    schema_version: Literal["agent-enrollment-import-result/v1"] = Field(
        default="agent-enrollment-import-result/v1",
        alias="schemaVersion",
    )
    status: Literal["imported", "unchanged", "blocked"]
    request_id: str | None = Field(default=None, alias="requestId")
    evidence_ref: str | None = Field(default=None, alias="evidenceRef")
    blocking_reasons: list[str] = Field(default_factory=list, alias="blockingReasons")


class AgentEnrollmentDecision(StrictModel):
    schema_version: Literal["agent-enrollment-decision/v1"] = Field(
        default="agent-enrollment-decision/v1",
        alias="schemaVersion",
    )
    status: Literal["approved", "rejected", "unchanged", "blocked"]
    request_id: str = Field(alias="requestId")
    enrollment_id: str | None = Field(default=None, alias="enrollmentId")
    device_id: str | None = Field(default=None, alias="deviceId")
    principal_id: str | None = Field(default=None, alias="principalId")
    evidence_ref: str | None = Field(default=None, alias="evidenceRef")
    blocking_reasons: list[str] = Field(default_factory=list, alias="blockingReasons")


class EnrolledAgent(StrictModel):
    schema_version: Literal["enrolled-agent/v1"] = Field(
        default="enrolled-agent/v1",
        alias="schemaVersion",
    )
    enrollment_id: str = Field(alias="enrollmentId")
    workspace_id: str = Field(alias="workspaceId")
    agent_id: str = Field(alias="agentId")
    principal_id: str = Field(alias="principalId")
    device_id: str = Field(alias="deviceId")
    token_id: str = Field(alias="tokenId")
    status: Literal["pending_approval", "active", "suspended", "revoked"]
    capabilities: tuple[str, ...]
    policy_profile: str = Field(alias="policyProfile", min_length=1)
    created_at_utc: datetime = Field(alias="createdAtUtc")
    last_seen_at_utc: datetime | None = Field(default=None, alias="lastSeenAtUtc")

    @field_validator("enrollment_id", "workspace_id", "agent_id", "principal_id", "device_id", "token_id")
    @classmethod
    def _safe_ids(cls, value: str, info: object) -> str:
        return _validate_safe_id(value, str(getattr(info, "field_name", "id")))

    @field_validator("capabilities")
    @classmethod
    def _capabilities(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        capabilities = tuple(sorted(set(value)))
        if not capabilities:
            raise ValueError("capabilities cannot be empty")
        return capabilities


def generate_raw_enrollment_token() -> str:
    return f"enr_{secrets.token_urlsafe(32)}"


def hash_enrollment_token(raw_token: str, *, token_id: str, workspace_id: str) -> str:
    normalized = raw_token.strip()
    if not normalized:
        raise ValueError("raw token cannot be empty")
    return sha256_text(f"{workspace_id}|{token_id}|{normalized}")


def token_proof_hash(raw_token: str, *, token_id: str, workspace_id: str) -> str:
    return sha256_text(f"proof|{workspace_id}|{token_id}|{raw_token.strip()}")


class AgentEnrollmentRequestCreateResult(StrictModel):
    schema_version: Literal["agent-enrollment-request-create-result/v1"] = Field(
        default="agent-enrollment-request-create-result/v1",
        alias="schemaVersion",
    )
    status: Literal["created", "blocked"]
    request: AgentEnrollmentRequest | None = None
    output_path: str | None = Field(default=None, alias="outputPath")
    raw_token_persisted: Literal[False] = Field(default=False, alias="rawTokenPersisted")
    blocking_reasons: list[str] = Field(default_factory=list, alias="blockingReasons")

    @model_validator(mode="after")
    def _created_requires_request(self) -> AgentEnrollmentRequestCreateResult:
        if self.status == "created" and self.request is None:
            raise ValueError("created result requires request")
        return self
