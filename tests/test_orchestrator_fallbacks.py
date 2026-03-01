import time

from binliquid.core.llm_ollama import StubLLM
from binliquid.core.orchestrator import Orchestrator
from binliquid.core.planner import PlannerRun
from binliquid.experts.base import ExpertBase
from binliquid.router.rule_router import RuleRouter
from binliquid.runtime.config import RuntimeConfig, RuntimeLimits
from binliquid.schemas.models import (
    ExpertName,
    ExpertRequest,
    ExpertResult,
    ExpertStatus,
    PlannerOutput,
    ResponseMode,
    TaskType,
)
from binliquid.schemas.reason_codes import ReasonCode
from binliquid.telemetry.tracer import Tracer


class StaticPlanner:
    def __init__(self, output: PlannerOutput):
        self.output = output

    def plan(self, user_input: str) -> PlannerRun:
        del user_input
        return PlannerRun(
            output=self.output,
            raw_output="{}",
            parse_failed=False,
            error=None,
            elapsed_ms=1,
            reason_code=ReasonCode.PLANNER_OK,
        )


class SlowResearchExpert(ExpertBase):
    name = ExpertName.RESEARCH

    def run(self, request: ExpertRequest) -> ExpertResult:
        del request
        time.sleep(0.05)
        return ExpertResult(
            expert_name=self.name,
            status=ExpertStatus.OK,
            confidence=0.5,
            payload={
                "summary": "slow",
                "evidence": [],
                "citations": [],
                "uncertainty": 0.5,
            },
            elapsed_ms=50,
        )


class FastPlanExpert(ExpertBase):
    name = ExpertName.PLAN

    def run(self, request: ExpertRequest) -> ExpertResult:
        del request
        return ExpertResult(
            expert_name=self.name,
            status=ExpertStatus.OK,
            confidence=0.8,
            payload={
                "plan_steps": ["A", "B"],
                "state_summary": "ok",
                "memory_candidates": [],
                "confidence": 0.8,
            },
            elapsed_ms=1,
        )


class FailingExpert(ExpertBase):
    name = ExpertName.RESEARCH

    def __init__(self) -> None:
        self.calls = 0

    def run(self, request: ExpertRequest) -> ExpertResult:
        del request
        self.calls += 1
        raise RuntimeError("boom")


class MixedResearchExpert(ExpertBase):
    name = ExpertName.RESEARCH

    def run(self, request: ExpertRequest) -> ExpertResult:
        del request
        return ExpertResult(
            expert_name=self.name,
            status=ExpertStatus.OK,
            confidence=0.8,
            payload={
                "summary": "research_view",
                "evidence": ["e1"],
                "citations": [],
                "uncertainty": 0.2,
            },
            elapsed_ms=1,
        )


class MixedPlanExpert(ExpertBase):
    name = ExpertName.PLAN

    def run(self, request: ExpertRequest) -> ExpertResult:
        del request
        return ExpertResult(
            expert_name=self.name,
            status=ExpertStatus.OK,
            confidence=0.8,
            payload={
                "plan_steps": ["A", "B"],
                "state_summary": "plan_view",
                "memory_candidates": ["A"],
                "confidence": 0.8,
            },
            elapsed_ms=1,
        )


def _config(timeout_ms: int = 10, threshold: int = 3, cooldown_s: int = 300) -> RuntimeConfig:
    limits = RuntimeLimits(
        expert_timeout_ms=timeout_ms,
        max_retries=0,
        circuit_breaker_threshold=threshold,
        circuit_breaker_cooldown_s=cooldown_s,
    )
    return RuntimeConfig(
        model_name="fake",
        profile_name="test",
        planner_temperature=0.0,
        answer_temperature=0.0,
        router_confidence_threshold=0.6,
        latency_budget_ms=1000,
        debug_mode=False,
        privacy_mode=True,
        enable_persistent_memory=False,
        web_enabled=False,
        trace_dir=".binliquid/test-traces",
        limits=limits,
    )


def test_orchestrator_timeout_uses_fallback_expert() -> None:
    planner_output = PlannerOutput(
        task_type=TaskType.RESEARCH,
        intent="research",
        needs_expert=True,
        expert_candidates=[ExpertName.RESEARCH, ExpertName.PLAN],
        confidence=0.95,
        latency_budget_ms=1000,
        can_fallback=True,
        response_mode=ResponseMode.TOOL_FIRST,
    )
    planner = StaticPlanner(planner_output)
    llm = StubLLM(responses=["final from llm"])
    router = RuleRouter(confidence_threshold=0.6)
    experts = {
        ExpertName.RESEARCH.value: SlowResearchExpert(),
        ExpertName.PLAN.value: FastPlanExpert(),
    }
    orchestrator = Orchestrator(
        planner=planner,
        llm=llm,
        router=router,
        experts=experts,
        tracer=Tracer(),
        config=_config(timeout_ms=10),
    )

    result = orchestrator.process("research this", use_router=True)

    assert result.used_path == "expert:plan_expert"
    assert any("fallback_expert_used:plan_expert" in item for item in result.fallback_events)


def test_orchestrator_opens_circuit_breaker_after_threshold() -> None:
    planner_output = PlannerOutput(
        task_type=TaskType.RESEARCH,
        intent="research",
        needs_expert=True,
        expert_candidates=[ExpertName.RESEARCH],
        confidence=0.95,
        latency_budget_ms=1000,
        can_fallback=True,
        response_mode=ResponseMode.TOOL_FIRST,
    )

    failing = FailingExpert()
    orchestrator = Orchestrator(
        planner=StaticPlanner(planner_output),
        llm=StubLLM(responses=["x", "x", "x", "x"]),
        router=RuleRouter(confidence_threshold=0.6),
        experts={ExpertName.RESEARCH.value: failing},
        tracer=Tracer(),
        config=_config(timeout_ms=100, threshold=3, cooldown_s=600),
    )

    for _ in range(3):
        orchestrator.process("test", use_router=True)

    fourth = orchestrator.process("test", use_router=True)

    assert failing.calls == 3
    assert "CB_OPEN" in fourth.fallback_events
    assert fourth.metrics["router_reason_code"] == "CB_OPEN"


def test_orchestrator_adjudicates_mixed_expert_outputs() -> None:
    planner_output = PlannerOutput(
        task_type=TaskType.MIXED,
        intent="mixed",
        needs_expert=True,
        expert_candidates=[ExpertName.RESEARCH, ExpertName.PLAN],
        confidence=0.95,
        latency_budget_ms=1000,
        can_fallback=True,
        response_mode=ResponseMode.TOOL_FIRST,
    )

    orchestrator = Orchestrator(
        planner=StaticPlanner(planner_output),
        llm=StubLLM(responses=["adjudicated-final"]),
        router=RuleRouter(confidence_threshold=0.6),
        experts={
            ExpertName.RESEARCH.value: MixedResearchExpert(),
            ExpertName.PLAN.value: MixedPlanExpert(),
        },
        tracer=Tracer(),
        config=_config(timeout_ms=100),
    )

    result = orchestrator.process("mixed request", use_router=True)

    assert result.final_text == "adjudicated-final"
    assert result.used_path == "expert_adjudicated:research_expert+plan_expert"
    assert "expert_adjudication" in result.fallback_events
