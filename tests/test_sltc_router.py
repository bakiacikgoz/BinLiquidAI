from binliquid.router.sltc_router import SLTCRouter
from binliquid.schemas.models import PlannerOutput, ResponseMode, TaskType


def test_sltc_router_prefers_code_expert_for_code_task() -> None:
    router = SLTCRouter(confidence_threshold=0.55, decay=0.85, spike_threshold=0.5)
    planner = PlannerOutput(
        task_type=TaskType.CODE,
        intent="fix_bug",
        needs_expert=True,
        expert_candidates=["code_expert", "plan_expert"],
        confidence=0.9,
        latency_budget_ms=3000,
        can_fallback=True,
        response_mode=ResponseMode.TOOL_FIRST,
    )

    decision = router.decide(planner)

    assert decision.selected_expert in {"code_expert", "llm_only"}
    assert decision.reason_code in {"SLTC_SPIKE", "SLTC_SUBTHRESHOLD", "SLTC_FALLBACK_LLM"}


def test_sltc_router_low_confidence_falls_back_llm() -> None:
    router = SLTCRouter(confidence_threshold=0.7)
    planner = PlannerOutput(
        task_type=TaskType.RESEARCH,
        intent="summarize",
        needs_expert=True,
        expert_candidates=["research_expert"],
        confidence=0.2,
        latency_budget_ms=2500,
        can_fallback=True,
        response_mode=ResponseMode.TOOL_FIRST,
    )

    decision = router.decide(planner)

    assert decision.selected_expert == "llm_only"
    assert decision.reason_code == "LOW_CONFIDENCE"
