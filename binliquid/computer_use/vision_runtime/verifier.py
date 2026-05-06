from __future__ import annotations

from binliquid.computer_use.vision_runtime.models import (
    InputActionType,
    VerificationResult,
    VisionAction,
    VisionObservation,
)


class HashChangeVerifier:
    def verify(
        self,
        *,
        before: VisionObservation,
        action: VisionAction,
        after: VisionObservation,
    ) -> VerificationResult:
        del action
        changed = before.screenshot_hash != after.screenshot_hash
        return VerificationResult(
            verified=changed,
            confidence=0.9 if changed else 0.2,
            message="screen hash changed" if changed else "screen hash did not change",
        )


class ConservativeVisionStepVerifier:
    def verify(
        self,
        *,
        before: VisionObservation,
        action: VisionAction,
        after: VisionObservation,
    ) -> VerificationResult:
        if action.action_type in {InputActionType.WAIT, InputActionType.MOVE_MOUSE}:
            return VerificationResult(
                verified=True,
                confidence=0.75,
                message=f"{action.action_type.value} completed; screen change not required",
            )

        changed = before.screenshot_hash != after.screenshot_hash
        return VerificationResult(
            verified=changed,
            confidence=0.9 if changed else 0.2,
            message="screen hash changed" if changed else "screen hash did not change",
        )
