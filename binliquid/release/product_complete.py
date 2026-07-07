from __future__ import annotations

from pydantic import Field

from binliquid.memory.models import StrictModel
from binliquid.release_decision.models import NoShipItem, NoShipRegister


class ProductCompleteInput(StrictModel):
    assistant_preview_in_product_mode: bool = Field(
        default=False,
        alias="assistantPreviewInProductMode",
    )
    fake_model_discovery: bool = Field(default=False, alias="fakeModelDiscovery")
    assistant_system_knowledge_missing: bool = Field(
        default=False,
        alias="assistantSystemKnowledgeMissing",
    )
    assistant_system_knowledge_stale: bool = Field(
        default=False,
        alias="assistantSystemKnowledgeStale",
    )
    assistant_uncited_system_claim: bool = Field(
        default=False,
        alias="assistantUncitedSystemClaim",
    )
    assistant_generic_platform_answer: bool = Field(
        default=False,
        alias="assistantGenericPlatformAnswer",
    )
    assistant_knowledge_secret_leak: bool = Field(
        default=False,
        alias="assistantKnowledgeSecretLeak",
    )
    assistant_task_executed_without_proposal: bool = Field(
        default=False,
        alias="assistantTaskExecutedWithoutProposal",
    )
    assistant_task_submit_without_operator_confirmation: bool = Field(
        default=False,
        alias="assistantTaskSubmitWithoutOperatorConfirmation",
    )
    assistant_task_write_bypassed_approval: bool = Field(
        default=False,
        alias="assistantTaskWriteBypassedApproval",
    )
    assistant_task_destructive_allowed: bool = Field(
        default=False,
        alias="assistantTaskDestructiveAllowed",
    )
    assistant_task_unenrolled_agent_accepted: bool = Field(
        default=False,
        alias="assistantTaskUnenrolledAgentAccepted",
    )
    assistant_task_unknown_agent_accepted: bool = Field(
        default=False,
        alias="assistantTaskUnknownAgentAccepted",
    )
    assistant_task_cross_workspace_allowed: bool = Field(
        default=False,
        alias="assistantTaskCrossWorkspaceAllowed",
    )
    assistant_task_raw_secret_leak: bool = Field(
        default=False,
        alias="assistantTaskRawSecretLeak",
    )
    assistant_task_prompt_injection_executed: bool = Field(
        default=False,
        alias="assistantTaskPromptInjectionExecuted",
    )
    assistant_task_idempotency_conflict_accepted: bool = Field(
        default=False,
        alias="assistantTaskIdempotencyConflictAccepted",
    )
    assistant_task_sourceless_system_claim: bool = Field(
        default=False,
        alias="assistantTaskSourcelessSystemClaim",
    )
    inert_primary_action: bool = Field(default=False, alias="inertPrimaryAction")
    enterprise_workspace_setup_bypass: bool = Field(
        default=False,
        alias="enterpriseWorkspaceSetupBypass",
    )
    agent_enrollment_raw_token_leak: bool = Field(
        default=False,
        alias="agentEnrollmentRawTokenLeak",
    )
    external_agent_not_enrolled_accepted: bool = Field(
        default=False,
        alias="externalAgentNotEnrolledAccepted",
    )
    memory_cross_workspace_allowed: bool = Field(
        default=False,
        alias="memoryCrossWorkspaceAllowed",
    )
    unrestricted_live_computer_use_claim: bool = Field(
        default=False,
        alias="unrestrictedLiveComputerUseClaim",
    )
    public_cloud_saas_claim: bool = Field(default=False, alias="publicCloudSaasClaim")
    public_installer_signed_claim_without_evidence: bool = Field(
        default=False,
        alias="publicInstallerSignedClaimWithoutEvidence",
    )
    local_product_overbroad_platform_claim: bool = Field(
        default=False,
        alias="localProductOverbroadPlatformClaim",
    )
    platform_claim_without_evidence: bool = Field(
        default=False,
        alias="platformClaimWithoutEvidence",
    )
    platform_evidence_commit_mismatch: bool = Field(
        default=False,
        alias="platformEvidenceCommitMismatch",
    )
    platform_evidence_target_mismatch: bool = Field(
        default=False,
        alias="platformEvidenceTargetMismatch",
    )
    platform_evidence_secret_leak: bool = Field(
        default=False,
        alias="platformEvidenceSecretLeak",
    )
    platform_evidence_stale: bool = Field(default=False, alias="platformEvidenceStale")
    unbounded_platform_support_claim: bool = Field(
        default=False,
        alias="unboundedPlatformSupportClaim",
    )
    source_install_target_without_evidence: bool = Field(
        default=False,
        alias="sourceInstallTargetWithoutEvidence",
    )
    source_install_target_stale: bool = Field(
        default=False,
        alias="sourceInstallTargetStale",
    )
    source_install_target_blocked: bool = Field(
        default=False,
        alias="sourceInstallTargetBlocked",
    )
    release_claim_overclaim: bool = Field(default=False, alias="releaseClaimOverclaim")


def _blocker(
    *,
    reason_code: str,
    claim_id: str,
    resolution_path: str,
) -> NoShipItem:
    return NoShipItem(
        id=reason_code,
        severity="blocker",
        status="open",
        claimId=claim_id,
        reasonCode=reason_code,
        resolutionPath=resolution_path,
    )


def build_product_complete_no_ship_register(
    input_state: ProductCompleteInput | None = None,
) -> NoShipRegister:
    state = input_state or ProductCompleteInput()
    items: list[NoShipItem] = []
    if state.assistant_preview_in_product_mode:
        items.append(
            _blocker(
                reason_code="ASSISTANT_PREVIEW_IN_PRODUCT_MODE",
                claim_id="real_ai_assistant_runtime",
                resolution_path=(
                    "Disable preview fixtures in product mode and route turns through "
                    "the assistant bridge."
                ),
            )
        )
    if state.fake_model_discovery:
        items.append(
            _blocker(
                reason_code="ASSISTANT_MODEL_DISCOVERY_FAKE",
                claim_id="assistant_model_discovery",
                resolution_path=(
                    "Use provider registry/model discovery or show setup-required diagnostics."
                ),
            )
        )
    if state.assistant_system_knowledge_missing:
        items.append(
            _blocker(
                reason_code="ASSISTANT_SYSTEM_KNOWLEDGE_MISSING",
                claim_id="assistant_system_knowledge",
                resolution_path="Build and verify the local assistant system knowledge index.",
            )
        )
    if state.assistant_system_knowledge_stale:
        items.append(
            _blocker(
                reason_code="ASSISTANT_SYSTEM_KNOWLEDGE_STALE",
                claim_id="assistant_system_knowledge",
                resolution_path="Rebuild the knowledge manifest after source changes.",
            )
        )
    if state.assistant_uncited_system_claim:
        items.append(
            _blocker(
                reason_code="ASSISTANT_UNCITED_SYSTEM_CLAIM",
                claim_id="assistant_system_knowledge",
                resolution_path="Require local source citations for AegisOS platform claims.",
            )
        )
    if state.assistant_generic_platform_answer:
        items.append(
            _blocker(
                reason_code="ASSISTANT_GENERIC_PLATFORM_ANSWER",
                claim_id="assistant_system_knowledge",
                resolution_path="Block generic platform answers and ground usage in local sources.",
            )
        )
    if state.assistant_knowledge_secret_leak:
        items.append(
            _blocker(
                reason_code="ASSISTANT_KNOWLEDGE_SECRET_LEAK",
                claim_id="assistant_system_knowledge",
                resolution_path="Exclude or redact the leaking source and keep the gate failing.",
            )
        )
    task_blockers = (
        (
            state.assistant_task_executed_without_proposal,
            "ASSISTANT_TASK_EXECUTED_WITHOUT_PROPOSAL",
            "Require a persisted AssistantTaskPlan before any task submission.",
        ),
        (
            state.assistant_task_submit_without_operator_confirmation,
            "ASSISTANT_TASK_SUBMIT_WITHOUT_OPERATOR_CONFIRMATION",
            "Require confirmPlanHash and operator id before submit.",
        ),
        (
            state.assistant_task_write_bypassed_approval,
            "ASSISTANT_TASK_WRITE_BYPASSED_APPROVAL",
            "Route external writes to approval-required status before execution.",
        ),
        (
            state.assistant_task_destructive_allowed,
            "ASSISTANT_TASK_DESTRUCTIVE_ALLOWED",
            "Keep destructive assistant tasking denied and non-submittable.",
        ),
        (
            state.assistant_task_unenrolled_agent_accepted,
            "ASSISTANT_TASK_UNENROLLED_AGENT_ACCEPTED",
            "Reject unenrolled agents before gateway submission.",
        ),
        (
            state.assistant_task_unknown_agent_accepted,
            "ASSISTANT_TASK_UNKNOWN_AGENT_ACCEPTED",
            "Reject unknown agents before gateway submission.",
        ),
        (
            state.assistant_task_cross_workspace_allowed,
            "ASSISTANT_TASK_CROSS_WORKSPACE_ALLOWED",
            "Enforce workspace binding during plan and submit.",
        ),
        (
            state.assistant_task_raw_secret_leak,
            "ASSISTANT_TASK_RAW_SECRET_LEAK",
            "Redact task artifacts and keep raw prompts/secrets out of persistence.",
        ),
        (
            state.assistant_task_prompt_injection_executed,
            "ASSISTANT_TASK_PROMPT_INJECTION_EXECUTED",
            "Treat LLM/user task text as untrusted and deny policy-bypass prompts.",
        ),
        (
            state.assistant_task_idempotency_conflict_accepted,
            "ASSISTANT_TASK_IDEMPOTENCY_CONFLICT_ACCEPTED",
            "Reject changed payloads with reused idempotency keys.",
        ),
        (
            state.assistant_task_sourceless_system_claim,
            "ASSISTANT_TASK_SOURCELESS_SYSTEM_CLAIM",
            "Cite local tasking docs and evidence refs for system claims.",
        ),
    )
    for enabled, reason_code, resolution_path in task_blockers:
        if enabled:
            items.append(
                _blocker(
                    reason_code=reason_code,
                    claim_id="assistant_governed_tasking",
                    resolution_path=resolution_path,
                )
            )
    if state.inert_primary_action:
        items.append(
            _blocker(
                reason_code="OPERATOR_INERT_PRIMARY_ACTION",
                claim_id="operator_panel_productization",
                resolution_path=(
                    "Classify the action as working, disabled_with_reason, or preview_only."
                ),
            )
        )
    if state.enterprise_workspace_setup_bypass:
        items.append(
            _blocker(
                reason_code="ENTERPRISE_WORKSPACE_SETUP_BYPASS",
                claim_id="enterprise_workspace_first_run",
                resolution_path=(
                    "Require identity/workspace readiness before enterprise-ready claims."
                ),
            )
        )
    if state.agent_enrollment_raw_token_leak:
        items.append(
            _blocker(
                reason_code="AGENT_ENROLLMENT_RAW_TOKEN_LEAK",
                claim_id="agent_enrollment",
                resolution_path=(
                    "Keep raw tokens shown-once only and store hashes in durable artifacts."
                ),
            )
        )
    if state.external_agent_not_enrolled_accepted:
        items.append(
            _blocker(
                reason_code="EXTERNAL_AGENT_NOT_ENROLLED_ACCEPTED",
                claim_id="external_agent_gateway",
                resolution_path=(
                    "Reject unknown or unenrolled external agents before action submission."
                ),
            )
        )
    if state.memory_cross_workspace_allowed:
        items.append(
            _blocker(
                reason_code="MEMORY_CROSS_WORKSPACE_ALLOWED",
                claim_id="workspace_memory_boundary",
                resolution_path="Enforce workspace-scoped memory ACLs and add denial evidence.",
            )
        )
    if state.unrestricted_live_computer_use_claim:
        items.append(
            _blocker(
                reason_code="COMPUTER_USE_UNQUALIFIED_CLAIM",
                claim_id="qualified_execution_surfaces",
                resolution_path=(
                    "Keep live computer-use qualification-gated with platform evidence."
                ),
            )
        )
    if state.public_cloud_saas_claim:
        items.append(
            _blocker(
                reason_code="PUBLIC_CLOUD_SAAS_OUT_OF_SCOPE",
                claim_id="product_boundary",
                resolution_path=(
                    "Remove public multi-tenant SaaS claims from product-complete scope."
                ),
            )
        )
    if state.public_installer_signed_claim_without_evidence:
        items.append(
            _blocker(
                reason_code="PUBLIC_INSTALLER_UNSIGNED_CLAIM",
                claim_id="desktop_public_release",
                resolution_path=(
                    "Attach real signing/notarization evidence or keep the claim internal-only."
                ),
            )
        )
    if state.local_product_overbroad_platform_claim:
        items.append(
            _blocker(
                reason_code="LOCAL_PRODUCT_OVERBROAD_PLATFORM_CLAIM",
                claim_id="local_product_platform_readiness",
                resolution_path=(
                    "Limit product support claims to evidenced platform/architecture targets "
                    "and keep not-evidenced targets out of supported claims."
                ),
            )
        )
    platform_blockers = [
        (
            state.platform_claim_without_evidence,
            "PLATFORM_CLAIM_WITHOUT_EVIDENCE",
            "Remove the unsupported claim or import matching platform evidence.",
        ),
        (
            state.platform_evidence_commit_mismatch,
            "PLATFORM_EVIDENCE_COMMIT_MISMATCH",
            "Regenerate platform evidence on the release candidate commit.",
        ),
        (
            state.platform_evidence_target_mismatch,
            "PLATFORM_EVIDENCE_TARGET_MISMATCH",
            "Use evidence whose target matches the claimed OS/architecture.",
        ),
        (
            state.platform_evidence_secret_leak,
            "PLATFORM_EVIDENCE_SECRET_LEAK",
            "Remove leaked sensitive content and regenerate the evidence bundle.",
        ),
        (
            state.platform_evidence_stale,
            "PLATFORM_EVIDENCE_STALE",
            "Refresh stale platform evidence before making a support claim.",
        ),
        (
            state.unbounded_platform_support_claim,
            "UNBOUNDED_PLATFORM_SUPPORT_CLAIM",
            "Replace broad platform claims with explicit evidenced target claims.",
        ),
    ]
    for enabled, reason_code, resolution_path in platform_blockers:
        if enabled:
            items.append(
                _blocker(
                    reason_code=reason_code,
                    claim_id="platform_evidence_reconciliation",
                    resolution_path=resolution_path,
                )
            )
    source_install_blockers = [
        (
            state.source_install_target_without_evidence,
            "SOURCE_INSTALL_TARGET_WITHOUT_EVIDENCE",
            "Remove the target from source install RC claims or import matching evidence.",
        ),
        (
            state.source_install_target_stale,
            "SOURCE_INSTALL_TARGET_STALE",
            "Regenerate source install evidence on the release candidate commit.",
        ),
        (
            state.source_install_target_blocked,
            "SOURCE_INSTALL_TARGET_BLOCKED",
            "Fix the blocked source install evidence verification result.",
        ),
        (
            state.release_claim_overclaim,
            "SOURCE_INSTALL_OVERCLAIM",
            "Restrict release text to the source install targets allowed by evidence.",
        ),
    ]
    for enabled, reason_code, resolution_path in source_install_blockers:
        if enabled:
            items.append(
                _blocker(
                    reason_code=reason_code,
                    claim_id="source_install_rc_claim",
                    resolution_path=resolution_path,
                )
            )
    return NoShipRegister(status="clear", items=items)
