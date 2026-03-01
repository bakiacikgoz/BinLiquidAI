from binliquid.router.rule_router import RuleRouter
from binliquid.schemas.models import PlannerOutput, ResponseMode, TaskType


def _planner(task_type: TaskType, confidence: float = 0.9) -> PlannerOutput:
    return PlannerOutput(
        task_type=task_type,
        intent="x",
        needs_expert=True,
        expert_candidates=["research_expert", "plan_expert", "code_expert"],
        confidence=confidence,
        latency_budget_ms=2000,
        can_fallback=True,
        response_mode=ResponseMode.TOOL_FIRST,
    )


def test_rule_router_routes_code_to_code_expert() -> None:
    router = RuleRouter(confidence_threshold=0.6)
    decision = router.decide(_planner(TaskType.CODE))
    assert decision.selected_expert == "code_expert"


def test_rule_router_low_confidence_goes_llm_only() -> None:
    router = RuleRouter(confidence_threshold=0.6)
    decision = router.decide(_planner(TaskType.RESEARCH, confidence=0.3))
    assert decision.selected_expert == "llm_only"
    assert decision.reason_code == "LOW_CONFIDENCE"


def test_rule_router_routes_plan_to_plan_expert() -> None:
    router = RuleRouter(confidence_threshold=0.6)
    decision = router.decide(_planner(TaskType.PLAN))
    assert decision.selected_expert == "plan_expert"
