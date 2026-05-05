from __future__ import annotations

from binliquid.computer_use.vision_runtime.drivers.base import PlatformDriverReadiness


def readiness() -> PlatformDriverReadiness:
    return PlatformDriverReadiness(
        platform="windows",
        live_execution_enabled=False,
        reason_code="WINDOWS_COMPUTER_USE_NOT_QUALIFIED",
        summary="Windows live computer-use remains disabled until signed qualification passes.",
    )
