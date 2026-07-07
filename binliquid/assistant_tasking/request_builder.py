from __future__ import annotations

from datetime import datetime

from binliquid.assistant_tasking.errors import AssistantTaskingError
from binliquid.assistant_tasking.models import (
    AssistantTaskPlan,
    AssistantTaskRiskClass,
    AssistantTaskSubmissionRequest,
    sha256_payload,
)
from binliquid.control_plane.external_contracts import (
    ExternalAgentActionV11,
    ExternalAgentRequestV11,
)


def build_external_agent_request(
    plan: AssistantTaskPlan,
    submit_request: AssistantTaskSubmissionRequest,
) -> ExternalAgentRequestV11:
    if submit_request.confirm_plan_hash != plan.plan_hash:
        raise AssistantTaskingError(
            "ASSISTANT_TASK_PLAN_HASH_MISMATCH",
            "confirmPlanHash does not match proposal planHash",
        )
    if not plan.safe_to_submit or plan.selected_agent is None:
        raise AssistantTaskingError(
            "ASSISTANT_TASK_SUBMIT_DISABLED",
            "task plan is not safe to submit",
        )
    risk = plan.risk_class
    if risk not in {AssistantTaskRiskClass.READ_ONLY, AssistantTaskRiskClass.EXTERNAL_WRITE}:
        raise AssistantTaskingError(
            "ASSISTANT_TASK_RISK_NOT_SUBMITTABLE",
            "only read-only and approval-required external write plans are submittable",
        )
    action_kind = "read" if risk == AssistantTaskRiskClass.READ_ONLY else "external_write"
    risk_hint = "read_only" if risk == AssistantTaskRiskClass.READ_ONLY else "external_write"
    return ExternalAgentRequestV11(
        requestId=plan.proposal_id,
        agentId=plan.selected_agent.agent_id,
        workflowId=f"assistant-tasking.{plan.proposal_id}",
        intent=plan.task_summary,
        actions=[
            ExternalAgentActionV11(
                actionId=f"assistant.{action_kind}",
                kind=action_kind,
                targetRef="assistant-tasking",
                effect=plan.task_summary[:500],
            )
        ],
        idempotencyKey=plan.idempotency_key,
        requestedBy=submit_request.operator_id,
        riskHint=risk_hint,
        requestedAt=datetime.fromisoformat(plan.created_at_utc.replace("Z", "+00:00")),
        metadata={
            "proposalId": plan.proposal_id,
            "planHash": plan.plan_hash,
            "taskSummaryHash": sha256_payload(plan.task_summary),
        },
    )
