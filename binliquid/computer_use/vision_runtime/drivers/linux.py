from __future__ import annotations

from binliquid.computer_use.vision_runtime.drivers.base import PlatformDriverReadiness


def readiness() -> PlatformDriverReadiness:
    return PlatformDriverReadiness(
        platform="linux",
        live_execution_enabled=False,
        reason_code="COMPUTER_USE_PLATFORM_NOT_QUALIFIED",
        summary="Linux live computer-use is scaffolded but not qualified.",
    )
