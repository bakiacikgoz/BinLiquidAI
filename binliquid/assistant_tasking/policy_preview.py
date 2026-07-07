from __future__ import annotations

from binliquid.assistant_tasking.models import (
    AssistantTaskPolicyDecision,
    AssistantTaskRiskClass,
    PolicyPreview,
)


def preview_policy(risk: AssistantTaskRiskClass, *, agent_blocked: bool = False) -> PolicyPreview:
    if agent_blocked:
        return PolicyPreview(
            decision=AssistantTaskPolicyDecision.DENY,
            riskClass=risk,
            approvalRequired=False,
            safeToSubmit=False,
            reasonCode="ASSISTANT_TASK_AGENT_BLOCKED",
            blockedReasons=("ASSISTANT_TASK_AGENT_BLOCKED",),
        )
    if risk == AssistantTaskRiskClass.READ_ONLY:
        return PolicyPreview(
            decision=AssistantTaskPolicyDecision.ALLOW,
            riskClass=risk,
            approvalRequired=False,
            safeToSubmit=True,
            reasonCode="ASSISTANT_TASK_READ_ONLY_ALLOWED",
        )
    if risk == AssistantTaskRiskClass.EXTERNAL_WRITE:
        return PolicyPreview(
            decision=AssistantTaskPolicyDecision.REQUIRE_APPROVAL,
            riskClass=risk,
            approvalRequired=True,
            safeToSubmit=True,
            reasonCode="ASSISTANT_TASK_WRITE_REQUIRES_APPROVAL",
        )
    reason = {
        AssistantTaskRiskClass.DESTRUCTIVE: "ASSISTANT_TASK_DESTRUCTIVE_DENIED",
        AssistantTaskRiskClass.CREDENTIAL_SENSITIVE: "ASSISTANT_TASK_CREDENTIAL_DENIED",
        AssistantTaskRiskClass.MUTATION: "ASSISTANT_TASK_PROMPT_INJECTION_DENIED",
    }.get(risk, "ASSISTANT_TASK_UNKNOWN_RISK_DENIED")
    return PolicyPreview(
        decision=AssistantTaskPolicyDecision.DENY,
        riskClass=risk,
        approvalRequired=False,
        safeToSubmit=False,
        reasonCode=reason,
        blockedReasons=(reason,),
    )
