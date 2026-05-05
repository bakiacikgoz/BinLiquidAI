from __future__ import annotations

from binliquid.computer_use.vision_runtime.models import (
    StopDecision,
    VisionAction,
    VisionInterpretation,
)


def first_candidate_or_done(interpretation: VisionInterpretation) -> VisionAction | StopDecision:
    if interpretation.candidate_actions:
        return interpretation.candidate_actions[0]
    return StopDecision(reason="done", summary="No candidate actions remain.")
