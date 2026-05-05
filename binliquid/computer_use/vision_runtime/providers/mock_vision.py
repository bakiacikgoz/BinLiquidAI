from __future__ import annotations

from collections.abc import Iterable

from binliquid.computer_use.models import WorldModel
from binliquid.computer_use.vision_runtime.models import (
    StopDecision,
    VerificationResult,
    VisionAction,
    VisionInterpretation,
    VisionObservation,
)


class DeterministicScreenCapture:
    def __init__(self, observations: Iterable[VisionObservation]) -> None:
        self._observations = list(observations)
        self._index = 0

    def capture(self) -> VisionObservation:
        if not self._observations:
            raise RuntimeError("no deterministic observations configured")
        if self._index >= len(self._observations):
            return self._observations[-1]
        observation = self._observations[self._index]
        self._index += 1
        return observation


class DeterministicActionPlanner:
    def __init__(self, actions: Iterable[VisionAction | StopDecision]) -> None:
        self._actions = list(actions)
        self._index = 0

    def next_action(
        self,
        *,
        objective: str,
        interpretation: VisionInterpretation,
        world: WorldModel | None,
    ) -> VisionAction | StopDecision:
        del objective, interpretation, world
        if self._index >= len(self._actions):
            return StopDecision(reason="done", summary="No more deterministic actions.")
        action = self._actions[self._index]
        self._index += 1
        return action


class DeterministicStepVerifier:
    def __init__(self, results: Iterable[VerificationResult]) -> None:
        self._results = list(results)
        self._index = 0

    def verify(
        self,
        *,
        before: VisionObservation,
        action: VisionAction,
        after: VisionObservation,
    ) -> VerificationResult:
        del before, action, after
        if self._index >= len(self._results):
            return VerificationResult(verified=True, confidence=1.0, message="default pass")
        result = self._results[self._index]
        self._index += 1
        return result
