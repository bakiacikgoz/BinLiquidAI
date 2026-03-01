from __future__ import annotations

import time

from binliquid.experts.base import ExpertBase
from binliquid.schemas.models import ExpertRequest, ExpertResult, ExpertStatus


class PlanLiteExpert(ExpertBase):
    name = "plan_expert"

    def run(self, request: ExpertRequest) -> ExpertResult:
        started = time.perf_counter()
        normalized = request.user_input.replace("?", ".")
        chunks = [piece.strip() for piece in normalized.split(".") if piece.strip()]
        if not chunks:
            chunks = [request.user_input.strip()]

        plan_steps = [f"Adım {index + 1}: {chunk}" for index, chunk in enumerate(chunks[:5])]
        payload = {
            "plan_steps": plan_steps,
            "state_summary": "Kullanıcı isteği adımlara bölündü.",
            "memory_candidates": chunks[:3],
        }
        elapsed = int((time.perf_counter() - started) * 1000)
        return ExpertResult(
            expert_name=self.name,
            status=ExpertStatus.OK,
            confidence=0.72,
            payload=payload,
            elapsed_ms=elapsed,
        )
