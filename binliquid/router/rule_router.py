from __future__ import annotations

from dataclasses import dataclass

from binliquid.schemas.models import PlannerOutput, RouterDecision, TaskType


@dataclass(slots=True)
class RuleRouter:
    confidence_threshold: float = 0.6

    def decide(self, planner_output: PlannerOutput) -> RouterDecision:
        if planner_output.confidence < self.confidence_threshold:
            return RouterDecision(
                selected_expert="llm_only",
                selection_confidence=planner_output.confidence,
                estimated_cost=0.1,
                estimated_latency_ms=planner_output.latency_budget_ms,
                fallback_expert=None,
                reason_code="LOW_CONFIDENCE",
            )

        if not planner_output.needs_expert or not planner_output.expert_candidates:
            return RouterDecision(
                selected_expert="llm_only",
                selection_confidence=planner_output.confidence,
                estimated_cost=0.1,
                estimated_latency_ms=max(100, planner_output.latency_budget_ms // 2),
                fallback_expert=None,
                reason_code="NO_EXPERT_NEEDED",
            )

        preferred = self._preferred_expert(planner_output.task_type)
        candidate_set = set(planner_output.expert_candidates)
        selected = preferred if preferred in candidate_set else planner_output.expert_candidates[0]
        fallback = self._fallback_expert(selected, planner_output.expert_candidates)

        return RouterDecision(
            selected_expert=selected,
            selection_confidence=planner_output.confidence,
            estimated_cost=0.5,
            estimated_latency_ms=min(planner_output.latency_budget_ms, 2000),
            fallback_expert=fallback,
            reason_code="RULE_ROUTE",
        )

    @staticmethod
    def _preferred_expert(task_type: TaskType) -> str:
        mapping = {
            TaskType.CODE: "code_expert",
            TaskType.RESEARCH: "research_expert",
            TaskType.PLAN: "plan_expert",
            TaskType.MIXED: "research_expert",
            TaskType.CHAT: "llm_only",
        }
        return mapping.get(task_type, "llm_only")

    @staticmethod
    def _fallback_expert(selected: str, candidates: list[str]) -> str | None:
        for candidate in candidates:
            if candidate != selected:
                return candidate
        return None
