from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

MemoryScope = Literal["session", "team", "case"]


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    ESCALATED = "escalated"


class AgentDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    agent_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    allowed_task_types: list[str] = Field(default_factory=list)
    profile_name: str | None = None
    model_overrides: dict[str, str] = Field(default_factory=dict)
    memory_scope_access: list[MemoryScope] = Field(default_factory=lambda: ["session"])
    tool_policy_profile: str | None = None
    approval_mode: Literal["auto", "always", "never"] = "auto"


class HandoffRule(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    from_role: str
    to_role: str
    required: bool = True


class TeamTerminationRules(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    max_tasks: int = Field(default=64, ge=1)
    max_retries: int = Field(default=1, ge=0)
    max_handoff_depth: int = Field(default=8, ge=1)


class TeamDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    team_id: str = Field(min_length=1)
    agents: list[AgentDefinition] = Field(min_length=1)
    supervisor_policy: str = "sequential_then_parallel"
    handoff_rules: list[HandoffRule] = Field(default_factory=list)
    termination_rules: TeamTerminationRules = Field(default_factory=TeamTerminationRules)


class TaskDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    task_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    task_type: str = Field(min_length=1)
    role: str = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    input_template: str | None = None


class TeamSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    version: str = "1"
    team: TeamDefinition
    tasks: list[TaskDefinition] = Field(default_factory=list)


class TaskRun(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    task_id: str
    parent_task_id: str | None = None
    assigned_agent_id: str
    role: str
    input_payload: dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    attempt_count: int = Field(default=0, ge=0)
    approval_state: str = "none"
    result_payload: dict[str, Any] = Field(default_factory=dict)
    reason_code: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobRun(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    job_id: str
    case_id: str
    team_id: str
    request: str
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    final_output: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class HandoffRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    from_agent: str
    to_agent: str
    payload: dict[str, Any]
    payload_hash: str
    policy_decision: str
    redaction_applied: bool
    approval_id: str | None = None


class TeamEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    event: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    team_id: str
    case_id: str
    job_id: str
    task_id: str | None = None
    agent_id: str | None = None
    role: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class AuditIntegrity(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    prev_hash: str | None = None
    hash: str
    signature: str | None = None


class AuditEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    envelope_version: str = "1"
    job_id: str
    case_id: str
    team_id: str
    policy_bundle_id: str
    policy_bundle_hash: str
    runtime_config_hash: str
    started_at: datetime
    finished_at: datetime
    decision_chain: list[dict[str, Any]] = Field(default_factory=list)
    approvals: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    handoffs: list[dict[str, Any]] = Field(default_factory=list)
    redaction_report: dict[str, Any] = Field(default_factory=dict)
    integrity: AuditIntegrity


class TeamRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    job: JobRun
    tasks: list[TaskRun]
    events: list[TeamEvent]
    handoffs: list[HandoffRecord]
    audit_envelope_path: str | None = None
