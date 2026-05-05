from __future__ import annotations

from binliquid.computer_use.vision_runtime.models import (
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
