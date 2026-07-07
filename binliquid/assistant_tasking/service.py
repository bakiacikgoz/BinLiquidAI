from __future__ import annotations

from binliquid.assistant_tasking.agent_catalog import resolve_agent_candidates, select_candidate
from binliquid.assistant_tasking.errors import AssistantTaskingError
from binliquid.assistant_tasking.intent import classify_intent, classify_risk, extract_agent_hint
from binliquid.assistant_tasking.models import (
    AssistantTaskIntentKind,
    AssistantTaskPlan,
    AssistantTaskPlanRequest,
    AssistantTaskPlanStatus,
    AssistantTaskPolicyDecision,
    AssistantTaskRiskClass,
    AssistantTaskSubmissionRequest,
    AssistantTaskSubmissionResult,
    EvidenceExpectation,
    sha256_payload,
    sha256_text,
    utc_now_iso,
)
from binliquid.assistant_tasking.policy_preview import preview_policy
from binliquid.assistant_tasking.redaction import contains_secret_marker, redact_text
from binliquid.assistant_tasking.request_builder import build_external_agent_request
from binliquid.assistant_tasking.store import AssistantTaskStore
from binliquid.control_plane.external_gateway import ExternalAgentGateway
from binliquid.control_plane.registry import AgentRegistry
from binliquid.runtime.config import RuntimeConfig

SOURCE_REFS = (
    "docs/ASSISTANT_GOVERNED_TASKING.md",
    "docs/EXTERNAL_AGENT_GATEWAY_GUIDE.md",
    "docs/AGENT_CONTROL_PLANE_ADAPTER_CONTRACT.md",
)


def plan_task(
    request: AssistantTaskPlanRequest,
    *,
    store: AssistantTaskStore | None = None,
) -> AssistantTaskPlan:
    redacted_message = redact_text(request.message)
    intent = classify_intent(redacted_message)
    risk = classify_risk(redacted_message)
    agent_hint = request.agent_hint or extract_agent_hint(redacted_message) or "external-agent"
    candidates = resolve_agent_candidates(
        root_dir=request.root_dir,
        workspace_id=request.workspace_id,
        agent_hint=agent_hint,
    )
    selected = select_candidate(candidates)
    blocked = list(selected.blocking_reasons if selected is not None else ())
    if contains_secret_marker(request.message):
        risk = AssistantTaskRiskClass.CREDENTIAL_SENSITIVE
        blocked.append("ASSISTANT_TASK_RAW_SECRET_LEAK")
    if intent == AssistantTaskIntentKind.UNSUPPORTED_DESTRUCTIVE:
        risk = AssistantTaskRiskClass.DESTRUCTIVE
    policy = preview_policy(risk, agent_blocked=bool(blocked))
    blocked.extend(reason for reason in policy.blocked_reasons if reason not in blocked)
    status = (
        AssistantTaskPlanStatus.PLANNED
        if policy.safe_to_submit and not blocked
        else AssistantTaskPlanStatus.BLOCKED
    )
    if intent == AssistantTaskIntentKind.CLARIFICATION_REQUIRED:
        status = AssistantTaskPlanStatus.CLARIFICATION_REQUIRED
        blocked.append("ASSISTANT_TASK_CLARIFICATION_REQUIRED")
    proposal_seed = f"{request.workspace_id}|{request.operator_id}|{redacted_message}|{agent_hint}"
    proposal_id = "astp_" + sha256_text(proposal_seed)[:24]
    idempotency_key = "assistant-task:" + sha256_text(proposal_seed)[:32]
    summary = _summary_for(redacted_message, risk)
    plan_without_hash = {
        "proposalId": proposal_id,
        "intentKind": intent,
        "agentId": selected.agent_id if selected else None,
        "taskSummary": summary,
        "riskClass": risk,
        "policyDecision": policy.decision,
        "idempotencyKey": idempotency_key,
        "blockedReasons": sorted(set(blocked)),
    }
    plan = AssistantTaskPlan(
        proposalId=proposal_id,
        planHash=sha256_payload(plan_without_hash),
        status=status,
        intentKind=intent,
        selectedAgent=selected,
        candidateAgents=candidates,
        taskSummary=summary,
        riskClass=risk,
        policyPreview=policy,
        approvalRequired=policy.approval_required,
        submitMode=(
            "proposal_first"
            if policy.safe_to_submit and not blocked
            else "disabled_with_reason"
        ),
        idempotencyKey=idempotency_key,
        evidenceExpectation=EvidenceExpectation(
            expectedRefs=(
                f"artifacts/assistant-tasking/proposals/{proposal_id}.json",
                f"external-gateway/evidence/{proposal_id}.json",
            )
        ),
        safeToSubmit=policy.safe_to_submit and not blocked,
        blockedReasons=tuple(sorted(set(blocked))),
        sourceRefs=SOURCE_REFS,
        createdAtUtc=utc_now_iso(),
    )
    (store or AssistantTaskStore()).write_plan(plan)
    return plan


def submit_task(
    request: AssistantTaskSubmissionRequest,
    *,
    store: AssistantTaskStore | None = None,
) -> AssistantTaskSubmissionResult:
    task_store = store or AssistantTaskStore()
    plan = task_store.read_plan(request.proposal_id)
    if plan is None:
        result = _blocked_result(
            proposal_id=request.proposal_id,
            plan_hash=request.confirm_plan_hash,
            reason_code="ASSISTANT_TASK_PROPOSAL_MISSING",
        )
        task_store.write_submission(result)
        return result
    try:
        external_request = build_external_agent_request(plan, request)
    except AssistantTaskingError as exc:
        result = _blocked_result(
            proposal_id=plan.proposal_id,
            plan_hash=plan.plan_hash,
            reason_code=exc.reason_code,
        )
        task_store.write_submission(result)
        return result
    gateway = ExternalAgentGateway(
        config=RuntimeConfig.from_profile(request.profile),
        registry=AgentRegistry(root_dir=request.root_dir),
        root_dir=request.root_dir,
    )
    response = gateway.submit_action_v1_1(external_request)
    result = AssistantTaskSubmissionResult(
        proposalId=plan.proposal_id,
        planHash=plan.plan_hash,
        status=response.status,
        policyDecision=response.policy_decision,
        reasonCode=response.reason_code,
        runId=response.run_id,
        approvalId=response.approval_id,
        evidenceRef=response.evidence_ref,
        replayStatus=response.replay_status,
        idempotencyStatus=response.idempotency_status,
        blockedReasons=(
            ()
            if response.status in {"accepted", "blocked_pending_approval"}
            else (response.reason_code,)
        ),
        nextActions=(
            ("evidence.inspect", "approval.review")
            if response.approval_id
            else ("evidence.inspect",)
        ),
        generatedAtUtc=utc_now_iso(),
    )
    task_store.write_submission(result)
    return result


def status_task(proposal_id: str, *, store: AssistantTaskStore | None = None):
    return (store or AssistantTaskStore()).status(proposal_id)


def explain_task(proposal_id: str, *, store: AssistantTaskStore | None = None) -> dict[str, object]:
    status = status_task(proposal_id, store=store)
    return {
        "schemaVersion": "assistant-tasking.explain/v1",
        "proposalId": proposal_id,
        "status": status.status,
        "sources": list(SOURCE_REFS),
        "evidenceRefs": list(status.evidence_refs),
        "policy": status.plan.policy_preview.model_dump(mode="json", by_alias=True)
        if status.plan
        else None,
        "blockingReasons": list(status.blocking_reasons),
    }


def _blocked_result(
    *,
    proposal_id: str,
    plan_hash: str,
    reason_code: str,
) -> AssistantTaskSubmissionResult:
    return AssistantTaskSubmissionResult(
        proposalId=proposal_id,
        planHash=plan_hash,
        status="denied" if "MISSING" not in reason_code else "invalid_request",
        policyDecision=AssistantTaskPolicyDecision.DENY,
        reasonCode=reason_code,
        blockedReasons=(reason_code,),
        nextActions=("assistant.task.plan",),
        generatedAtUtc=utc_now_iso(),
    )


def _summary_for(message: str, risk: AssistantTaskRiskClass) -> str:
    if risk == AssistantTaskRiskClass.READ_ONLY:
        return f"Ask the selected external agent to inspect and summarize: {message[:220]}"
    if risk == AssistantTaskRiskClass.EXTERNAL_WRITE:
        return f"Prepare an approval-required external write task: {message[:220]}"
    return f"Do not submit this unsafe assistant task: {message[:220]}"
