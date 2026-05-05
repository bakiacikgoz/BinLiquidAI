from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from binliquid.governance.models import ApprovalTicket
from binliquid.team.models import JobRun, TaskRun, TeamEvent


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)


class ComputerUseCapabilityContract(ContractModel):
    enabled: bool
    stage: str
    platform: str
    scope: str
    execution_modes: list[str] = Field(alias="executionModes")
    replayable: bool
    fail_closed: bool = Field(alias="failClosed")
    adapter_status: str = Field(alias="adapterStatus")
    reason_code: str | None = Field(default=None, alias="reasonCode")
    summary: str | None = None


class ComputerUseVisionRuntimeCapabilityContract(ContractModel):
    enabled: bool
    stage: Literal["configured", "not_configured", "not_qualified", "qualified"]
    platform: Literal["macos", "windows", "linux", "unknown"]
    scope: Literal["vision_first_desktop_web_file"]
    execution_modes: list[str] = Field(alias="executionModes")
    replayable: bool
    fail_closed: bool = Field(alias="failClosed")
    reason_code: str | None = Field(default=None, alias="reasonCode")
    summary: str | None = None


class OperatorFeatureFlagsContract(ContractModel):
    operator_workflow_parity: bool = Field(alias="operatorWorkflowParity")
    enterprise_ops_parity: bool = Field(alias="enterpriseOpsParity")
    computer_use_pilot: ComputerUseCapabilityContract = Field(alias="computerUsePilot")
    computer_use_vision_runtime: ComputerUseVisionRuntimeCapabilityContract = Field(
        alias="computerUseVisionRuntime"
    )


class OperatorCommandCapabilitiesContract(ContractModel):
    approval_pending_json: bool = Field(alias="approvalPendingJson")
    approval_show_json: bool = Field(alias="approvalShowJson")
    approval_decide: bool = Field(alias="approvalDecide")
    approval_execute: bool = Field(alias="approvalExecute")
    computer_use_submit: bool = Field(alias="computerUseSubmit")
    computer_use_pause: bool = Field(alias="computerUsePause")
    computer_use_resume: bool = Field(alias="computerUseResume")
    computer_use_stop: bool = Field(alias="computerUseStop")
    computer_use_state_json: bool = Field(alias="computerUseStateJson")
    team_submit: bool = Field(alias="teamSubmit")
    team_resume_submit: bool = Field(alias="teamResumeSubmit")
    team_list_json: bool = Field(alias="teamListJson")
    team_status_json: bool = Field(alias="teamStatusJson")
    team_replay_json: bool = Field(alias="teamReplayJson")
    config_resolve_json: bool = Field(alias="configResolveJson")
    auth_whoami_json: bool = Field(alias="authWhoamiJson")
    auth_check_json: bool = Field(alias="authCheckJson")
    security_baseline_json: bool = Field(alias="securityBaselineJson")
    keys_status_json: bool = Field(alias="keysStatusJson")
    keys_verify_json: bool = Field(alias="keysVerifyJson")
    keys_rotate_plan_json: bool = Field(alias="keysRotatePlanJson")
    support_bundle_export_json: bool = Field(alias="supportBundleExportJson")
    metrics_snapshot_json: bool = Field(alias="metricsSnapshotJson")
    ga_readiness_json: bool = Field(alias="gaReadinessJson")
    qualification_run_json: bool = Field(alias="qualificationRunJson")
    backup_create_json: bool = Field(alias="backupCreateJson")
    backup_verify_json: bool = Field(alias="backupVerifyJson")
    restore_verify_json: bool = Field(alias="restoreVerifyJson")
    migrate_plan_json: bool = Field(alias="migratePlanJson")
    migrate_apply_dry_run_json: bool = Field(alias="migrateApplyDryRunJson")


class OperatorCapabilitiesPayload(ContractModel):
    core_version: str = Field(alias="coreVersion")
    contract_version: Literal["2.0"] = Field(alias="contractVersion")
    profiles: list[str]
    preview_mode: bool | None = Field(default=None, alias="previewMode")
    features: OperatorFeatureFlagsContract
    commands: OperatorCommandCapabilitiesContract
    artifact_schema: dict[str, str] = Field(default_factory=dict, alias="artifactSchema")


class BridgeHandshakeContract(ContractModel):
    ui_version: str = Field(alias="uiVersion")
    core_version: str = Field(alias="coreVersion")
    profile: str
    contract_version: Literal["2.0"] = Field(alias="contractVersion")
    capabilities: OperatorCapabilitiesPayload
    doctor: dict[str, Any]
    root_dir: str = Field(alias="rootDir")
    mode: str


class SpawnedRunPayloadContract(ContractModel):
    contract_version: Literal["2.0"] = Field(alias="contractVersion")
    job_id: str = Field(alias="jobId")
    profile: str
    root_dir: str = Field(alias="rootDir")
    process_id: int | None = Field(alias="processId")


class ApprovalPendingPayloadContract(ContractModel):
    contract_version: Literal["2.0"]
    pending: list[ApprovalTicket] = Field(default_factory=list)


class ApprovalDetailPayloadContract(ContractModel):
    contract_version: Literal["2.0"]
    approval_id: str
    status: str
    execution_status: str
    ticket: ApprovalTicket


class RunSummaryItemContract(ContractModel):
    job_id: str
    case_id: str
    team_id: str
    status: str
    request: str
    created_at: str
    finished_at: str
    audit_envelope_path: str
    job_dir: str


class RunSummaryPayloadContract(ContractModel):
    contract_version: Literal["2.0"]
    status: str
    root_dir: str
    count: int
    items: list[RunSummaryItemContract] = Field(default_factory=list)
    errors: list[dict[str, str]] = Field(default_factory=list)


class TeamStatusArtifactContract(ContractModel):
    contract_version: Literal["2.0"]
    job: JobRun
    tasks: list[TaskRun] = Field(default_factory=list)
    audit_envelope_path: str | None = None
    job_dir: str | None = None
    resume_outcomes: list[dict[str, Any]] = Field(default_factory=list)
    continuation: dict[str, Any] = Field(default_factory=dict)
    computer_use: dict[str, Any] = Field(default_factory=dict)


class RunReplayPayloadContract(ContractModel):
    contract_version: Literal["2.0"]
    job_id: str
    status: str | None = None
    team_id: str | None = None
    case_id: str | None = None
    final_output: str | None = None
    event_count: int
    task_event_count: int
    handoff_event_count: int
    approval_event_count: int
    decision_count: int
    integrity: dict[str, Any] = Field(default_factory=dict)
    trace_refs: list[str] = Field(default_factory=list)
    approvals: list[dict[str, Any]] = Field(default_factory=list)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    handoffs: list[dict[str, Any]] = Field(default_factory=list)
    verified: bool | None = None
    errors: list[str] = Field(default_factory=list)
    checks: dict[str, Any] = Field(default_factory=dict)
    consistency: dict[str, Any] = Field(default_factory=dict)


class ReadArtifactPayloadContract(ContractModel):
    contract_version: Literal["2.0"] = Field(alias="contractVersion")
    artifact_name: str = Field(alias="artifactName")
    payload: dict[str, Any] = Field(default_factory=dict)
    truncated: bool
    bytes_read: int = Field(alias="bytesRead")


class TailEventsPayloadContract(ContractModel):
    contract_version: Literal["2.0"] = Field(alias="contractVersion")
    events: list[TeamEvent] = Field(default_factory=list)
    next_cursor: int = Field(alias="nextCursor")
    reset: bool
    truncated: bool
    bad_line_count: int = Field(alias="badLineCount")


class ConfigResolvePayloadContract(ContractModel):
    contract_version: Literal["2.0"]
    profile: str
    status: str
    resolved: dict[str, Any] = Field(default_factory=dict)
    source_map: dict[str, Any] = Field(default_factory=dict)


class AuthWhoAmIPayloadContract(ContractModel):
    contract_version: Literal["2.0"]
    identity_enabled: bool
    verified: bool
    actor: dict[str, Any] | None = None
    error_code: str | None = None
    error: str | None = None


class AuthCheckPayloadContract(ContractModel):
    contract_version: Literal["2.0"]
    permission: str
    allowed: bool
    actor: dict[str, Any] | None = None
    error_code: str | None = None
    error: str | None = None


class SecurityBaselinePayloadContract(ContractModel):
    contract_version: Literal["2.0"]
    profile: str
    overall_status: str
    checks: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    roots: dict[str, str] = Field(default_factory=dict)
    key_status: dict[str, Any] = Field(default_factory=dict)
    misconfiguration_risks: list[str] = Field(default_factory=list)


class KeyStatusPayloadContract(ContractModel):
    contract_version: Literal["2.0"]
    provider: str
    current_key_id: str | None = None
    private_key_path: str
    private_key_present: bool
    trusted_keys_dir: str
    trusted_key_count: int
    trusted_keys: list[str] = Field(default_factory=list)
    key_manifest_path: str
    key_manifest_present: bool
    compat_env_hmac_enabled: bool
    enterprise_compatible: bool
    pkcs11_status: str


class SupportBundleExportPayloadContract(ContractModel):
    contract_version: Literal["2.0"]
    bundle_dir: str
    archive_path: str
    manifest_path: str
    file_count: int


class DeviceActionApprovalSnapshotContract(ContractModel):
    kind: Literal["device_action"]
    target_kind: Literal["device_action"]
    action_hash: str
    policy_hash: str
    action_id: str
    category: str
    risk_class: str
    target_ref: str
    window_or_tab_identity: str
    window_identity: str
    app_identity: str
    selector_source: str
    selector_context: dict[str, Any] = Field(default_factory=dict)
    perception_fingerprint: str
    action_plan: dict[str, Any] = Field(default_factory=dict)
    execution_contract: dict[str, Any] = Field(default_factory=dict)


class PreviewFixtureOperationsContract(ContractModel):
    identity: AuthWhoAmIPayloadContract
    permission_check: AuthCheckPayloadContract = Field(alias="permissionCheck")
    security: SecurityBaselinePayloadContract
    keys: KeyStatusPayloadContract
    support: SupportBundleExportPayloadContract
    metrics: dict[str, Any] = Field(default_factory=dict)
    ga_readiness: dict[str, Any] = Field(default_factory=dict, alias="gaReadiness")
    qualification: dict[str, Any] = Field(default_factory=dict)
    backup_create: dict[str, Any] = Field(default_factory=dict, alias="backupCreate")
    backup_verify: dict[str, Any] = Field(default_factory=dict, alias="backupVerify")
    restore_verify: dict[str, Any] = Field(default_factory=dict, alias="restoreVerify")
    migrate_plan: dict[str, Any] = Field(default_factory=dict, alias="migratePlan")
    migrate_apply_dry_run: dict[str, Any] = Field(
        default_factory=dict,
        alias="migrateApplyDryRun",
    )


class PreviewFixtureArtifactsContract(ContractModel):
    status: TeamStatusArtifactContract
    tasks: dict[str, Any] = Field(default_factory=dict)
    handoffs: dict[str, Any] = Field(default_factory=dict)
    audit_envelope: dict[str, Any] = Field(default_factory=dict, alias="auditEnvelope")


class PreviewFixtureBundleContract(ContractModel):
    contract_version: Literal["2.0"] = Field(alias="contractVersion")
    handshake: BridgeHandshakeContract
    submit_team_run: SpawnedRunPayloadContract = Field(alias="submitTeamRun")
    approval_pending: ApprovalPendingPayloadContract = Field(alias="approvalPending")
    approval_detail: ApprovalDetailPayloadContract = Field(alias="approvalDetail")
    run_summary: RunSummaryPayloadContract = Field(alias="runSummary")
    run_detail: TeamStatusArtifactContract = Field(alias="runDetail")
    run_replay: RunReplayPayloadContract = Field(alias="runReplay")
    read_artifact: PreviewFixtureArtifactsContract = Field(alias="readArtifact")
    tail_events: TailEventsPayloadContract = Field(alias="tailEvents")
    config_resolve: ConfigResolvePayloadContract = Field(alias="configResolve")
    operations: PreviewFixtureOperationsContract
    device_action_snapshot: DeviceActionApprovalSnapshotContract = Field(
        alias="deviceActionSnapshot"
    )
