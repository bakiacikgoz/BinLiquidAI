from __future__ import annotations

from typing import Any

from binliquid.assistant_tasking.models import (
    AgentTaskCandidate,
    AssistantTaskPlan,
    AssistantTaskPolicyDecision,
    AssistantTaskRiskClass,
    AssistantTaskSubmissionResult,
    EvidenceExpectation,
    PolicyPreview,
    sha256_payload,
)

FIXTURE_TIME = "2026-01-01T00:00:00Z"


def _candidate(*, enrolled: bool = True, agent_id: str = "external-agent") -> AgentTaskCandidate:
    return AgentTaskCandidate(
        agentId=agent_id,
        label=agent_id,
        enrolled=enrolled,
        workspaceId="pilot-workspace",
        principalId="principal-agent",
        allowedSurfaces=("external_gateway",) if enrolled else (),
        blockedSurfaces=() if enrolled else ("external_gateway",),
        declaredActions=("read", "external_write"),
        qualificationStatus="ready" if enrolled else "blocked",
        blockingReasons=() if enrolled else ("ASSISTANT_TASK_UNENROLLED_AGENT_DENIED",),
    )


def _plan(
    *,
    proposal_id: str,
    risk: AssistantTaskRiskClass,
    decision: AssistantTaskPolicyDecision,
    safe: bool,
    reason: str,
    agent: AgentTaskCandidate | None = None,
) -> AssistantTaskPlan:
    selected = agent if agent is not None else _candidate()
    blocked = () if safe else (reason,)
    seed = {
        "proposalId": proposal_id,
        "agentId": selected.agent_id if selected else None,
        "riskClass": risk,
        "policyDecision": decision,
        "blockedReasons": blocked,
    }
    return AssistantTaskPlan(
        proposalId=proposal_id,
        planHash=sha256_payload(seed),
        status="planned" if safe else "blocked",
        intentKind="plan_agent_task",
        selectedAgent=selected,
        candidateAgents=(selected,) if selected else (),
        taskSummary=f"Fixture task for {proposal_id}",
        riskClass=risk,
        policyPreview=PolicyPreview(
            decision=decision,
            riskClass=risk,
            approvalRequired=decision == AssistantTaskPolicyDecision.REQUIRE_APPROVAL,
            safeToSubmit=safe,
            reasonCode=reason,
            blockedReasons=blocked,
        ),
        approvalRequired=decision == AssistantTaskPolicyDecision.REQUIRE_APPROVAL,
        submitMode="proposal_first" if safe else "disabled_with_reason",
        idempotencyKey=f"assistant-task:{proposal_id}",
        evidenceExpectation=EvidenceExpectation(
            expectedRefs=(f"artifacts/assistant-tasking/proposals/{proposal_id}.json",)
        ),
        safeToSubmit=safe,
        blockedReasons=blocked,
        sourceRefs=("docs/ASSISTANT_GOVERNED_TASKING.md",),
        createdAtUtc=FIXTURE_TIME,
    )


def contract_fixtures() -> dict[str, dict[str, Any]]:
    read = _plan(
        proposal_id="astp_read_only_fixture",
        risk=AssistantTaskRiskClass.READ_ONLY,
        decision=AssistantTaskPolicyDecision.ALLOW,
        safe=True,
        reason="ASSISTANT_TASK_READ_ONLY_ALLOWED",
    )
    write = _plan(
        proposal_id="astp_write_fixture",
        risk=AssistantTaskRiskClass.EXTERNAL_WRITE,
        decision=AssistantTaskPolicyDecision.REQUIRE_APPROVAL,
        safe=True,
        reason="ASSISTANT_TASK_WRITE_REQUIRES_APPROVAL",
    )
    destructive = _plan(
        proposal_id="astp_destructive_fixture",
        risk=AssistantTaskRiskClass.DESTRUCTIVE,
        decision=AssistantTaskPolicyDecision.DENY,
        safe=False,
        reason="ASSISTANT_TASK_DESTRUCTIVE_DENIED",
    )
    unknown = _plan(
        proposal_id="astp_unknown_fixture",
        risk=AssistantTaskRiskClass.UNKNOWN,
        decision=AssistantTaskPolicyDecision.DENY,
        safe=False,
        reason="ASSISTANT_TASK_UNKNOWN_AGENT_DENIED",
        agent=_candidate(enrolled=False, agent_id="unknown-agent"),
    )
    unenrolled = _plan(
        proposal_id="astp_unenrolled_fixture",
        risk=AssistantTaskRiskClass.READ_ONLY,
        decision=AssistantTaskPolicyDecision.DENY,
        safe=False,
        reason="ASSISTANT_TASK_UNENROLLED_AGENT_DENIED",
        agent=_candidate(enrolled=False, agent_id="external-agent"),
    )
    injection = _plan(
        proposal_id="astp_injection_fixture",
        risk=AssistantTaskRiskClass.MUTATION,
        decision=AssistantTaskPolicyDecision.DENY,
        safe=False,
        reason="ASSISTANT_TASK_PROMPT_INJECTION_DENIED",
    )
    conflict = AssistantTaskSubmissionResult(
        proposalId="astp_conflict_fixture",
        planHash=read.plan_hash,
        status="invalid_request",
        policyDecision="deny",
        reasonCode="ASSISTANT_TASK_IDEMPOTENCY_CONFLICT_ACCEPTED",
        blockedReasons=("ASSISTANT_TASK_IDEMPOTENCY_CONFLICT_ACCEPTED",),
        generatedAtUtc=FIXTURE_TIME,
    )
    return {
        "read_only_plan_pass.json": read.model_dump(mode="json", by_alias=True),
        "write_requires_approval.json": write.model_dump(mode="json", by_alias=True),
        "destructive_denied.json": destructive.model_dump(mode="json", by_alias=True),
        "unknown_agent_denied.json": unknown.model_dump(mode="json", by_alias=True),
        "unenrolled_agent_denied.json": unenrolled.model_dump(mode="json", by_alias=True),
        "prompt_injection_denied.json": injection.model_dump(mode="json", by_alias=True),
        "idempotency_conflict_blocked.json": conflict.model_dump(mode="json", by_alias=True),
        "raw_secret_leak_fail.json": {
            "schemaVersion": "assistant-tasking.raw-leak-fixture/v1",
            "expectedFailure": "ASSISTANT_TASK_RAW_SECRET_LEAK",
            "rawPromptIncluded": True,
            "rawSecretMarker": "token=[redacted-test-secret]",
        },
    }
