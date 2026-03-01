from __future__ import annotations

from dataclasses import dataclass, field

from binliquid.schemas.models import ExpertStatus, PlannerOutput, RouterDecision, TaskType


@dataclass(slots=True)
class ExpertTemporalState:
    membrane: float = 0.0
    successes: int = 0
    failures: int = 0
    last_latency_ms: int = 0


@dataclass(slots=True)
class SLTCRouter:
    """Binary spiking-inspired temporal router prototype (Phase 3)."""

    confidence_threshold: float = 0.6
    decay: float = 0.82
    spike_threshold: float = 0.55
    states: dict[str, ExpertTemporalState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for expert_name in ("llm_only", "code_expert", "research_expert", "plan_expert"):
            self.states.setdefault(expert_name, ExpertTemporalState())

    def decide(self, planner_output: PlannerOutput) -> RouterDecision:
        if planner_output.confidence < self.confidence_threshold:
            return RouterDecision(
                selected_expert="llm_only",
                selection_confidence=planner_output.confidence,
                estimated_cost=0.08,
                estimated_latency_ms=planner_output.latency_budget_ms,
                fallback_expert=None,
                reason_code="LOW_CONFIDENCE",
            )

        candidates = planner_output.expert_candidates or ["llm_only"]
        candidates = [
            candidate for candidate in candidates if candidate in self.states
        ] or ["llm_only"]

        scores: dict[str, float] = {}
        for candidate in candidates:
            state = self.states[candidate]
            spike_input = self._spike_input(
                candidate=candidate,
                planner_output=planner_output,
                state=state,
            )
            membrane = (self.decay * state.membrane) + spike_input
            state.membrane = membrane
            scores[candidate] = membrane

        selected = max(scores, key=scores.get)
        selected_score = scores[selected]
        reason_code = (
            "SLTC_SPIKE"
            if selected_score >= self.spike_threshold
            else "SLTC_SUBTHRESHOLD"
        )

        fallback = self._second_best(scores, selected)
        if selected_score < self.spike_threshold and "llm_only" in self.states:
            selected = "llm_only"
            fallback = fallback if fallback != "llm_only" else None
            reason_code = "SLTC_FALLBACK_LLM"

        return RouterDecision(
            selected_expert=selected,
            selection_confidence=max(
                0.0,
                min(1.0, planner_output.confidence * 0.95 + selected_score * 0.05),
            ),
            estimated_cost=self._estimate_cost(selected),
            estimated_latency_ms=self._estimate_latency_ms(
                selected,
                planner_output.latency_budget_ms,
            ),
            fallback_expert=fallback,
            reason_code=reason_code,
        )

    def update_feedback(self, expert_name: str, status: ExpertStatus, elapsed_ms: int) -> None:
        if expert_name not in self.states:
            return
        state = self.states[expert_name]
        state.last_latency_ms = elapsed_ms
        if status == ExpertStatus.OK:
            state.successes += 1
            state.membrane = max(0.0, state.membrane * 0.9)
        else:
            state.failures += 1
            state.membrane = max(0.0, state.membrane * 0.5)

    @staticmethod
    def _task_bias(task_type: TaskType, candidate: str) -> float:
        table = {
            TaskType.CHAT: {"llm_only": 0.25},
            TaskType.CODE: {"code_expert": 0.45, "plan_expert": 0.1},
            TaskType.RESEARCH: {"research_expert": 0.45, "plan_expert": 0.1},
            TaskType.PLAN: {"plan_expert": 0.45, "research_expert": 0.1},
            TaskType.MIXED: {"research_expert": 0.3, "plan_expert": 0.25, "code_expert": 0.2},
        }
        return table.get(task_type, {}).get(candidate, 0.0)

    def _spike_input(
        self,
        *,
        candidate: str,
        planner_output: PlannerOutput,
        state: ExpertTemporalState,
    ) -> float:
        failure_penalty = (state.failures / max(state.successes + state.failures, 1)) * 0.35
        latency_penalty = (
            0.12
            if (state.last_latency_ms and state.last_latency_ms > planner_output.latency_budget_ms)
            else 0
        )
        task_bias = self._task_bias(task_type=planner_output.task_type, candidate=candidate)
        need_bonus = 0.12 if planner_output.needs_expert and candidate != "llm_only" else 0.0
        conf_bonus = planner_output.confidence * 0.2

        return max(0.0, task_bias + need_bonus + conf_bonus - failure_penalty - latency_penalty)

    @staticmethod
    def _second_best(scores: dict[str, float], selected: str) -> str | None:
        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        for name, _score in ordered:
            if name != selected:
                return name
        return None

    @staticmethod
    def _estimate_cost(selected_expert: str) -> float:
        cost_table = {
            "llm_only": 0.08,
            "code_expert": 0.38,
            "research_expert": 0.3,
            "plan_expert": 0.24,
        }
        return cost_table.get(selected_expert, 0.3)

    @staticmethod
    def _estimate_latency_ms(selected_expert: str, budget_ms: int) -> int:
        latency_table = {
            "llm_only": int(budget_ms * 0.7),
            "code_expert": int(budget_ms * 0.95),
            "research_expert": int(budget_ms * 0.9),
            "plan_expert": int(budget_ms * 0.8),
        }
        return max(100, latency_table.get(selected_expert, budget_ms))
