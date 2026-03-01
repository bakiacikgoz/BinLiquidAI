from __future__ import annotations

from dataclasses import dataclass

from binliquid.schemas.models import RouterDecision


class SLTCRouterInterface:
    """Research-path contract for future sLTC router integration."""

    def decide(self, features: dict[str, float | int | str]) -> RouterDecision:  # pragma: no cover
        raise NotImplementedError


@dataclass(slots=True)
class PlaceholderSLTCRouter(SLTCRouterInterface):
    """No-op placeholder that keeps product path stable."""

    def decide(self, features: dict[str, float | int | str]) -> RouterDecision:
        del features
        return RouterDecision(
            selected_expert="llm_only",
            selection_confidence=0.0,
            estimated_cost=0.0,
            estimated_latency_ms=0,
            fallback_expert=None,
            reason_code="SLTC_PLACEHOLDER",
        )
